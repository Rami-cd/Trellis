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
    languages: list[str],
) -> None:
    session.execute(text("""
        INSERT INTO repositories (id, name, path)
        VALUES (:id, :name, :path)
        ON CONFLICT (id) DO UPDATE SET
            name = EXCLUDED.name,
            path = EXCLUDED.path
    """), {"id": repo_id, "name": name, "path": path})

    session.execute(text("DELETE FROM repository_languages WHERE repo_id = :id"), {"id": repo_id})

    session.execute(text("""INSERT INTO repository_languages (repo_id, language) VALUES (:repo_id, :language)"""),
        [{"repo_id": repo_id, "language": lang} for lang in languages])

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