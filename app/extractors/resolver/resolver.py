from sqlalchemy import text

from app.db.connection import SessionLocal
from app.db.repository import get_nodes_by_qualified_name


def resolve_call(edge_id: str, repo_id: str = "test_repo") -> None:
    session = SessionLocal()
    try:
        edge_target_ref = session.execute(
            text("SELECT target_ref FROM code_edges WHERE id = :edge_id"),
            {"edge_id": edge_id},
        ).scalar_one_or_none()

        if edge_target_ref is None:
            return

        get_nodes_by_qualified_name(
            session=session,
            qualified_name=str(edge_target_ref),
            repo_id=repo_id,
        )
    finally:
        session.close()
