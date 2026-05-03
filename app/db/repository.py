from __future__ import annotations

import json
from typing import Sequence

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas.edge import CodeEdge
from app.schemas.node import CodeNode

# ---------------------------------------------------------------------------
# Repository upsert
# ---------------------------------------------------------------------------

def upsert_repository(
    session: Session,
    repo_id: str,
    name: str,
    path: str,
    languages: list[str],
) -> None:
    session.execute(text("""
        INSERT INTO repositories (id, name, path)
        VALUES (:id, :name, :path)
        ON CONFLICT (id) DO UPDATE SET
            name = EXCLUDED.name,
            path = EXCLUDED.path,
            indexed_at = NOW()
    """), {"id": repo_id, "name": name, "path": path})

    session.execute(
        text("DELETE FROM repository_languages WHERE repo_id = :id"),
        {"id": repo_id},
    )

    if languages:
        session.execute(
            text("INSERT INTO repository_languages (repo_id, language) VALUES (:repo_id, :language)"),
            [{"repo_id": repo_id, "language": lang} for lang in languages],
        )

    session.commit()


# ---------------------------------------------------------------------------
# Insert — batched via executemany
# ---------------------------------------------------------------------------

def insert_nodes(
    session: Session,
    repo_id: str,
    nodes: Sequence[CodeNode],
) -> None:
    if not nodes:
        return

    session.execute(text("""
        INSERT INTO code_nodes (
            id, repo_id, name, type, path, qualified_name,
            start_line, end_line, start_byte, end_byte,
            language, raw_source, attributes
        )
        VALUES (
            :id, :repo_id, :name, :type, :path, :qualified_name,
            :start_line, :end_line, :start_byte, :end_byte,
            :language, :raw_source, CAST(:attributes AS JSONB)
        )
        ON CONFLICT (id) DO NOTHING
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
            "attributes": json.dumps(node.attributes),
        }
        for node in nodes
    ])

    session.commit()


def insert_edges(
    session: Session,
    edges: Sequence[CodeEdge],
) -> None:
    if not edges:
        return

    session.execute(text("""
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

    session.commit()


# ---------------------------------------------------------------------------
# Fetch — nodes
# ---------------------------------------------------------------------------

def get_nodes_by_repo(
    session: Session,
    repo_id: str,
) -> list[dict]:
    
    rows = session.execute(text("""
        SELECT
            id, repo_id, name, type, path, qualified_name,
            start_line, end_line, start_byte, end_byte,
            language, raw_source, attributes
        FROM code_nodes
        WHERE repo_id = :repo_id
        ORDER BY path, start_line
    """), {"repo_id": repo_id}).mappings().all()

    return [dict(row) for row in rows]


def get_node_by_id(
    session: Session,
    node_id: str,
) -> dict | None:
    
    row = session.execute(text("""
        SELECT
            id, repo_id, name, type, path, qualified_name,
            start_line, end_line, start_byte, end_byte,
            language, raw_source, attributes
        FROM code_nodes
        WHERE id = :node_id
    """), {"node_id": node_id}).mappings().first()

    return dict(row) if row else None


def get_nodes_by_ids(
    session: Session,
    node_ids: list[str],
) -> list[dict]:

    if not node_ids:
        return []

    rows = session.execute(text("""
        SELECT
            id, repo_id, name, type, path, qualified_name,
            start_line, end_line, start_byte, end_byte,
            language, raw_source, attributes
        FROM code_nodes
        WHERE id = ANY(:node_ids)
    """), {"node_ids": node_ids}).mappings().all()

    return [dict(row) for row in rows]


# ---------------------------------------------------------------------------
# Fetch — edges
# ---------------------------------------------------------------------------

def get_edges_by_node(
    session: Session,
    node_id: str,
) -> list[dict]:

    rows = session.execute(text("""
        SELECT id, source_id, target_id, target_ref, type, attributes
        FROM code_edges
        WHERE source_id = :node_id
           OR target_id = :node_id
    """), {"node_id": node_id}).mappings().all()

    return [dict(row) for row in rows]


# ---------------------------------------------------------------------------
# Fetch — subgraph (recursive CTE)
# ---------------------------------------------------------------------------

def get_subgraph(
    session: Session,
    seed_node_ids: list[str],
    depth: int = 2,
) -> dict[str, list[dict]]:

    if not seed_node_ids:
        return {"nodes": [], "edges": []}

    # Clamp depth to a sane upper bound — deep recursion on a large repo
    # will produce an enormous context window for the LLM.
    depth = min(depth, 5)

    rows = session.execute(text("""
        WITH RECURSIVE subgraph(node_id, level, path) AS (
            -- Base: seed nodes at level 0
            SELECT
                seed.node_id,
                0 AS level,
                ARRAY[seed.node_id]::text[] AS path
            FROM unnest(CAST(:seed_ids AS text[])) AS seed(node_id)

            UNION ALL

            -- Recursive: expand one hop along any edge, in either direction
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
    """), {"seed_ids": seed_node_ids, "depth": depth}).fetchall()

    discovered_ids = [row[0] for row in rows]

    if not discovered_ids:
        return {"nodes": [], "edges": []}

    nodes = get_nodes_by_ids(session, discovered_ids)

    edge_rows = session.execute(text("""
        SELECT id, source_id, target_id, target_ref, type, attributes
        FROM code_edges
        WHERE source_id = ANY(:ids)
          AND target_id = ANY(:ids)
    """), {"ids": discovered_ids}).mappings().all()

    edges = [dict(row) for row in edge_rows]

    return {"nodes": nodes, "edges": edges}
