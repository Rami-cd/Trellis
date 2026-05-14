from __future__ import annotations

import json
import uuid
from typing import Any, Sequence

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.edge import CodeEdge
from app.schemas.node import CodeNode, CodeNodeType


async def upsert_repository(
    session: AsyncSession,
    repo_id: str,
    name: str,
    path: str,
    languages: list[str],
    user_id: str | None = None,
) -> None:
    await session.execute(text("""
        INSERT INTO repositories (id, name, path, user_id)
        VALUES (:id, :name, :path, :user_id)
        ON CONFLICT (id) DO UPDATE SET
            name = EXCLUDED.name,
            path = EXCLUDED.path,
            user_id = EXCLUDED.user_id
    """), {"id": repo_id, "name": name, "path": path, "user_id": user_id})

    await session.execute(
        text("DELETE FROM repository_languages WHERE repo_id = :id"),
        {"id": repo_id},
    )

    if languages:
        await session.execute(
            text("INSERT INTO repository_languages (repo_id, language) VALUES (:repo_id, :language)"),
            [{"repo_id": repo_id, "language": lang} for lang in languages],
        )

    await session.commit()


async def insert_nodes(
    session: AsyncSession,
    repo_id: str,
    nodes: Sequence[CodeNode],
) -> None:
    if not nodes:
        return

    await session.execute(text("""
        INSERT INTO code_nodes (
            id, repo_id, name, type, path, qualified_name,
            start_line, end_line, start_byte, end_byte,
            language, raw_source, content_hash, attributes
        )
        VALUES (
            :id, :repo_id, :name, :type, :path, :qualified_name,
            :start_line, :end_line, :start_byte, :end_byte,
            :language, :raw_source, :content_hash, CAST(:attributes AS JSONB)
        )
        ON CONFLICT (id) DO UPDATE SET
            repo_id = EXCLUDED.repo_id,
            name = EXCLUDED.name,
            type = EXCLUDED.type,
            path = EXCLUDED.path,
            qualified_name = EXCLUDED.qualified_name,
            start_line = EXCLUDED.start_line,
            end_line = EXCLUDED.end_line,
            start_byte = EXCLUDED.start_byte,
            end_byte = EXCLUDED.end_byte,
            language = EXCLUDED.language,
            raw_source = EXCLUDED.raw_source,
            content_hash = EXCLUDED.content_hash,
            attributes = EXCLUDED.attributes
        WHERE code_nodes.content_hash IS DISTINCT FROM EXCLUDED.content_hash
    """), [
        {
            "id": node.id,
            "repo_id": repo_id,
            "name": node.name,
            "type": node.type.value,
            "path": node.path,
            "qualified_name": node.qualified_name,
            "start_line": node.start_line,
            "end_line": node.end_line,
            "start_byte": node.start_byte,
            "end_byte": node.end_byte,
            "language": node.language,
            "raw_source": node.raw_source,
            "content_hash": node.content_hash,
            "attributes": json.dumps(node.attributes),
        }
        for node in nodes
    ])

    await session.commit()


async def insert_edges(
    session: AsyncSession,
    edges: Sequence[CodeEdge],
) -> None:
    if not edges:
        return

    await session.execute(text("""
        INSERT INTO code_edges (
            id, source_id, target_id, target_ref, type, attributes
        )
        VALUES (
            :id, :source_id, :target_id, :target_ref, :type, CAST(:attributes AS JSONB)
        )
        ON CONFLICT (id) DO NOTHING
    """), [
        {
            "id": edge.id,
            "source_id": edge.source_id,
            "target_id": edge.target_id,
            "target_ref": edge.target_ref,
            "type": edge.type.value,
            "attributes": json.dumps(edge.attributes),
        }
        for edge in edges
    ])

    await session.commit()


async def get_nodes_by_repo(
    session: AsyncSession,
    repo_id: str,
) -> list[dict]:
    rows = (await session.execute(text("""
        SELECT
            id, repo_id, name, type, path, qualified_name,
            start_line, end_line, start_byte, end_byte,
            language, raw_source, content_hash, attributes
        FROM code_nodes
        WHERE repo_id = :repo_id
        ORDER BY path, start_line
    """), {"repo_id": repo_id})).mappings().all()

    return [dict(row) for row in rows]


async def get_repo_node_content_hashes(
    session: AsyncSession,
    repo_id: str,
) -> dict[str, dict[str, Any]]:
    rows = (await session.execute(text("""
        SELECT id, path, content_hash
        FROM code_nodes
        WHERE repo_id = :repo_id
    """), {"repo_id": repo_id})).mappings().all()

    return {
        row["id"]: {
            "path": row["path"],
            "content_hash": row["content_hash"],
        }
        for row in rows
    }


async def get_node_by_id(
    session: AsyncSession,
    node_id: str,
) -> dict | None:
    row = (await session.execute(text("""
        SELECT
            id, repo_id, name, type, path, qualified_name,
            start_line, end_line, start_byte, end_byte,
            language, raw_source, content_hash, attributes
        FROM code_nodes
        WHERE id = :node_id
    """), {"node_id": node_id})).mappings().first()

    return dict(row) if row else None


async def get_nodes_by_ids(
    session: AsyncSession,
    node_ids: list[str],
) -> list[dict]:
    if not node_ids:
        return []

    rows = (await session.execute(text("""
        SELECT
            id, repo_id, name, type, path, qualified_name,
            start_line, end_line, start_byte, end_byte,
            language, raw_source, content_hash, attributes
        FROM code_nodes
        WHERE id = ANY(:node_ids)
    """), {"node_ids": node_ids})).mappings().all()

    return [dict(row) for row in rows]


async def get_node_content_hashes(
    session: AsyncSession,
    node_ids: list[str],
) -> dict[str, str | None]:
    if not node_ids:
        return {}

    rows = (await session.execute(text("""
        SELECT id, content_hash
        FROM code_nodes
        WHERE id = ANY(:node_ids)
    """), {"node_ids": node_ids})).mappings().all()

    return {
        row["id"]: row["content_hash"]
        for row in rows
    }


async def get_edges_by_node(
    session: AsyncSession,
    node_id: str,
) -> list[dict]:
    rows = (await session.execute(text("""
        SELECT id, source_id, target_id, target_ref, type, attributes
        FROM code_edges
        WHERE source_id = :node_id
           OR target_id = :node_id
    """), {"node_id": node_id})).mappings().all()

    return [dict(row) for row in rows]


async def get_subgraph(
    session: AsyncSession,
    seed_node_ids: list[str],
    depth: int = 2,
) -> dict[str, list[dict]]:
    if not seed_node_ids:
        return {"nodes": [], "edges": []}

    depth = min(depth, 5)

    rows = (await session.execute(text("""
        WITH RECURSIVE subgraph(node_id, level, path) AS (
            SELECT
                seed.node_id,
                0 AS level,
                ARRAY[seed.node_id]::text[] AS path
            FROM unnest(CAST(:seed_ids AS text[])) AS seed(node_id)

            UNION ALL

            SELECT
                nxt.node_id,
                sg.level + 1,
                sg.path || nxt.node_id
            FROM subgraph sg
            JOIN code_edges e
                ON e.source_id = sg.node_id
                OR e.target_id = sg.node_id
            CROSS JOIN LATERAL (
                SELECT CASE
                    WHEN e.source_id = sg.node_id THEN e.target_id
                    ELSE e.source_id
                END AS node_id
            ) AS nxt
            WHERE sg.level < :depth
              AND nxt.node_id IS NOT NULL
              AND NOT (nxt.node_id = ANY(sg.path))
        )
        SELECT DISTINCT node_id FROM subgraph
    """), {"seed_ids": seed_node_ids, "depth": depth})).fetchall()

    discovered_ids = [row[0] for row in rows]

    if not discovered_ids:
        return {"nodes": [], "edges": []}

    nodes = await get_nodes_by_ids(session, discovered_ids)

    edge_rows = (await session.execute(text("""
        SELECT id, source_id, target_id, target_ref, type, attributes
        FROM code_edges
        WHERE source_id = ANY(:ids)
          AND target_id = ANY(:ids)
    """), {"ids": discovered_ids})).mappings().all()

    edges = [dict(row) for row in edge_rows]

    return {"nodes": nodes, "edges": edges}


async def fetch_by_repo(session: AsyncSession, repo_id: str) -> list[CodeNode]:
    rows = (await session.execute(text("""
        SELECT
            id, name, type, path, qualified_name,
            start_line, end_line, start_byte, end_byte,
            language, raw_source, content_hash, summary, attributes
        FROM code_nodes
        WHERE repo_id = :repo_id
        ORDER BY path, start_line
    """), {"repo_id": repo_id})).mappings().all()

    return [
        CodeNode(
            id=row["id"],
            name=row["name"],
            type=CodeNodeType(row["type"]),
            start_byte=row["start_byte"],
            end_byte=row["end_byte"],
            language=row["language"],
            path=row["path"],
            qualified_name=row["qualified_name"],
            start_line=row["start_line"],
            end_line=row["end_line"],
            attributes=dict(row["attributes"] or {}),
            raw_source=row["raw_source"],
            content_hash=row["content_hash"],
            summary=row["summary"],
        )
        for row in rows
    ]


async def delete_nodes(session: AsyncSession, node_ids: list[str]) -> None:
    await session.execute(
        text("DELETE FROM code_nodes WHERE id = ANY(:ids)"),
        {"ids": node_ids},
    )
    await session.commit()


async def update_summary(session: AsyncSession, node_id: str, summary: str) -> None:
    await session.execute(text("""
        UPDATE code_nodes
        SET summary = :summary
        WHERE id = :node_id
    """), {"node_id": node_id, "summary": summary})


async def upsert_embedding(
    session: AsyncSession,
    node_id: str,
    chunk_text: str,
    embedding: list[float],
) -> None:
    await session.execute(text("""
        INSERT INTO code_embeddings (node_id, chunk_index, chunk_text, embedding)
        VALUES (:node_id, 0, :chunk_text, CAST(:embedding AS vector))
        ON CONFLICT (node_id, chunk_index) DO UPDATE SET
            chunk_text = EXCLUDED.chunk_text,
            embedding = EXCLUDED.embedding
    """), {
        "node_id": node_id,
        "chunk_text": chunk_text,
        "embedding": json.dumps(embedding),
    })

async def get_repository(
    session: AsyncSession,
    repo_id: str,
) -> dict | None:
    row = (await session.execute(text("""
        SELECT r.id, r.name, r.path, r.user_id,
               COALESCE(array_agg(rl.language) FILTER (WHERE rl.language IS NOT NULL), '{}') AS languages
        FROM repositories r
        LEFT JOIN repository_languages rl ON rl.repo_id = r.id
        WHERE r.id = :repo_id
        GROUP BY r.id
    """), {"repo_id": repo_id})).mappings().first()

    return dict(row) if row else None


async def get_repositories_by_user(
    session: AsyncSession,
    user_id: str,
) -> list[dict]:
    rows = (await session.execute(text("""
        SELECT r.id, r.name, r.path, r.user_id,
               COALESCE(array_agg(rl.language) FILTER (WHERE rl.language IS NOT NULL), '{}') AS languages
        FROM repositories r
        LEFT JOIN repository_languages rl ON rl.repo_id = r.id
        WHERE r.user_id = :user_id
        GROUP BY r.id
        ORDER BY r.id
    """), {"user_id": user_id})).mappings().all()

    return [dict(row) for row in rows]


async def delete_repository(
    session: AsyncSession,
    repo_id: str,
) -> None:
    await session.execute(text("""
        DELETE FROM repositories WHERE id = :repo_id
    """), {"repo_id": repo_id})
    await session.commit()


async def create_conversation(
    session: AsyncSession,
    repo_id: str,
    user_id: str,
    title: str | None = None,
) -> str:
    conversation_id = str(uuid.uuid4())

    await session.execute(text("""
        INSERT INTO conversations (id, repo_id, user_id, title)
        VALUES (:id, :repo_id, :user_id, :title)
    """), {
        "id": conversation_id,
        "repo_id": repo_id,
        "user_id": user_id,
        "title": title,
    })
    await session.commit()

    return conversation_id


async def get_conversation(
    session: AsyncSession,
    conversation_id: str,
) -> dict | None:
    row = (await session.execute(text("""
        SELECT id, repo_id, user_id, title, created_at
        FROM conversations
        WHERE id = :conversation_id
    """), {"conversation_id": conversation_id})).mappings().first()

    return dict(row) if row else None


async def list_conversations(
    session: AsyncSession,
    repo_id: str,
    user_id: str,
) -> list[dict]:
    rows = (await session.execute(text("""
        SELECT id, repo_id, user_id, title, created_at
        FROM conversations
        WHERE repo_id = :repo_id
          AND user_id = :user_id
        ORDER BY created_at DESC, id DESC
    """), {
        "repo_id": repo_id,
        "user_id": user_id,
    })).mappings().all()

    return [dict(row) for row in rows]


async def create_message(
    session: AsyncSession,
    conversation_id: str,
    role: str,
    content: str,
    nodes_used: list[str] | None = None,
) -> str:
    message_id = str(uuid.uuid4())

    await session.execute(text("""
        INSERT INTO messages (id, conversation_id, role, content, nodes_used)
        VALUES (
            :id,
            :conversation_id,
            :role,
            :content,
            CAST(:nodes_used AS JSONB)
        )
    """), {
        "id": message_id,
        "conversation_id": conversation_id,
        "role": role,
        "content": content,
        "nodes_used": json.dumps(nodes_used) if nodes_used is not None else None,
    })
    await session.commit()

    return message_id


async def list_messages(
    session: AsyncSession,
    conversation_id: str,
) -> list[dict]:
    rows = (await session.execute(text("""
        SELECT id, conversation_id, role, content, nodes_used, created_at
        FROM messages
        WHERE conversation_id = :conversation_id
        ORDER BY created_at ASC, id ASC
    """), {"conversation_id": conversation_id})).mappings().all()

    return [dict(row) for row in rows]

async def update_node_by_id(
    session: AsyncSession,
    node_id: str,
    **kwargs: Any,
) -> None:
    set_clauses = []
    params = {"node_id": node_id}

    for key, value in kwargs.items():
        set_clauses.append(f"{key} = :{key}")
        params[key] = value

    if not set_clauses:
        return

    set_statement = ", ".join(set_clauses)

    await session.execute(text(f"""
        UPDATE code_nodes
        SET {set_statement}
        WHERE id = :node_id
    """), params)
    await session.commit()


async def get_nodes_with_embeddings(session: AsyncSession, repo_id: str) -> set[str]:
    rows = (await session.execute(text("""
        SELECT cn.id
        FROM code_nodes cn
        JOIN code_embeddings ce ON ce.node_id = cn.id
        WHERE cn.repo_id = :repo_id
    """), {"repo_id": repo_id})).fetchall()
    return {row[0] for row in rows}