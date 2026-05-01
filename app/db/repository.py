from __future__ import annotations
from typing import Sequence
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.schemas.edge import CodeEdge, CodeEdgeType
from app.schemas.node import CodeNode, CodeNodeType


def upsert_repository(
    session: Session,
    repo_id: str,
    name: str,
    path: str,
    language: str | None = None,
) -> None:
    session.execute(text("""
        INSERT INTO repositories (id, name, path, language)
        VALUES (:id, :name, :path, :language)
        ON CONFLICT (id) DO UPDATE SET
            name = EXCLUDED.name,
            path = EXCLUDED.path,
            language = EXCLUDED.language
    """), {"id": repo_id, "name": name, "path": path, "language": language})
    session.commit()


def insert_nodes(
    session: Session,
    repo_id: str,
    nodes: Sequence[CodeNode],
) -> None:
    for node in nodes:
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
        """), {
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
            "attributes": __import__("json").dumps(node.attributes),
        })
    session.commit()


def insert_edges(session: Session, edges: Sequence[CodeEdge]) -> None:
    for edge in edges:
        session.execute(text("""
            INSERT INTO code_edges (
                id, source_id, target_id, target_ref, type, attributes
            )
            VALUES (
                :id, :source_id, :target_id, :target_ref, :type, CAST(:attributes AS JSONB)
            )
            ON CONFLICT (id) DO NOTHING
        """), {
            "id": edge.id,
            "source_id": edge.source_id,
            "target_id": edge.target_id,
            "target_ref": edge.target_ref,
            "type": edge.type.value,
            "attributes": __import__("json").dumps(edge.attributes),
        })
    session.commit()


def get_node_by_id(session: Session, node_id: str) -> CodeNode | None:
    row = session.execute(
        text("SELECT * FROM code_nodes WHERE id = :id"),
        {"id": node_id}
    ).mappings().first()
    return _row_to_node(row) if row else None


def get_nodes_by_qualified_name(
    session: Session,
    qualified_name: str,
    repo_id: str | None = None,
) -> list[CodeNode]:
    query = "SELECT * FROM code_nodes WHERE qualified_name = :qn"
    params: dict = {"qn": qualified_name}
    if repo_id:
        query += " AND repo_id = :repo_id"
        params["repo_id"] = repo_id
    rows = session.execute(text(query), params).mappings().all()
    return [_row_to_node(r) for r in rows]


def get_nodes_by_path(
    session: Session,
    path: str,
    repo_id: str | None = None,
) -> list[CodeNode]:
    query = "SELECT * FROM code_nodes WHERE path = :path"
    params: dict = {"path": path}
    if repo_id:
        query += " AND repo_id = :repo_id"
        params["repo_id"] = repo_id
    rows = session.execute(text(query), params).mappings().all()
    return [_row_to_node(r) for r in rows]


def get_unresolved_edges(
    session: Session,
    repo_id: str | None = None,
) -> list[CodeEdge]:
    if repo_id:
        rows = session.execute(text("""
            SELECT e.* FROM code_edges e
            JOIN code_nodes n ON e.source_id = n.id
            WHERE e.target_id IS NULL AND n.repo_id = :repo_id
        """), {"repo_id": repo_id}).mappings().all()
    else:
        rows = session.execute(
            text("SELECT * FROM code_edges WHERE target_id IS NULL")
        ).mappings().all()
    return [_row_to_edge(r) for r in rows]


def resolve_edge(session: Session, edge_id: str, target_id: str) -> None:
    session.execute(text("""
        UPDATE code_edges SET target_id = :target_id WHERE id = :edge_id
    """), {"target_id": target_id, "edge_id": edge_id})
    session.commit()


def get_subgraph(
    session: Session,
    node_id: str,
    depth: int = 1,
) -> tuple[list[CodeNode], list[CodeEdge]]:
    rows = session.execute(text("""
        WITH RECURSIVE subgraph AS (
            SELECT id, 0 AS level FROM code_nodes WHERE id = :node_id
            UNION
            SELECT e.target_id, s.level + 1
            FROM code_edges e
            JOIN subgraph s ON e.source_id = s.id
            WHERE e.target_id IS NOT NULL AND s.level < :depth
        )
        SELECT DISTINCT n.* FROM code_nodes n
        JOIN subgraph s ON n.id = s.id
    """), {"node_id": node_id, "depth": depth}).mappings().all()

    nodes = [_row_to_node(r) for r in rows]
    node_ids = [n.id for n in nodes]

    edge_rows = session.execute(text("""
        SELECT * FROM code_edges
        WHERE source_id = ANY(:ids) AND target_id = ANY(:ids)
    """), {"ids": node_ids}).mappings().all()

    edges = [_row_to_edge(r) for r in edge_rows]
    return nodes, edges


# --- helpers ---

def _row_to_node(row) -> CodeNode:
    return CodeNode(
        id=row["id"],
        name=row["name"],
        type=CodeNodeType(row["type"]),
        path=row["path"],
        qualified_name=row["qualified_name"],
        start_line=row["start_line"],
        end_line=row["end_line"],
        start_byte=row["start_byte"],
        end_byte=row["end_byte"],
        language=row["language"],
        raw_source=row["raw_source"],
        attributes=_decode_attributes(row["attributes"]),
    )


def _row_to_edge(row) -> CodeEdge:
    return CodeEdge(
        id=row["id"],
        source_id=row["source_id"],
        target_id=row["target_id"],
        target_ref=row["target_ref"],
        type=CodeEdgeType(row["type"]),
        attributes=_decode_attributes(row["attributes"]),
    )


def _decode_attributes(value) -> dict:
    import json

    if not value:
        return {}
    if isinstance(value, str):
        return json.loads(value)
    return dict(value)
