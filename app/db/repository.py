from __future__ import annotations
from typing import Sequence
from sqlalchemy.orm import Session
from app.schemas.edge import CodeEdge
from app.schemas.node import CodeNode

def upsert_repository(
    session: Session,
    repo_id: str,
    name: str,
    path: str,
    language: str | None = None,
) -> None:
    """Create or update a repository record."""
    ...


def insert_nodes(
    session: Session,
    repo_id: str,
    nodes: Sequence[CodeNode],
) -> None:
    """Insert a collection of code nodes for a repository."""
    ...


def insert_edges(session: Session, edges: Sequence[CodeEdge]) -> None:
    """Insert a collection of code edges."""
    ...


def get_node_by_id(session: Session, node_id: str) -> CodeNode | None:
    """Fetch a single code node by its unique identifier."""
    ...


def get_nodes_by_qualified_name(
    session: Session,
    qualified_name: str,
    repo_id: str | None = None,
) -> list[CodeNode]:
    """Fetch code nodes matching a qualified name, optionally within one repository."""
    ...


def get_nodes_by_path(
    session: Session,
    path: str,
    repo_id: str | None = None,
) -> list[CodeNode]:
    """Fetch code nodes associated with a source path, optionally within one repository."""
    ...


def get_unresolved_edges(
    session: Session,
    repo_id: str | None = None,
) -> list[CodeEdge]:
    """Fetch edges whose target node has not been resolved yet."""
    ...


def resolve_edge(session: Session, edge_id: str, target_id: str) -> None:
    """Mark an edge as resolved by linking it to a target node."""
    ...


def get_subgraph(
    session: Session,
    node_id: str,
    depth: int = 1,
) -> tuple[list[CodeNode], list[CodeEdge]]:
    """Fetch the connected subgraph around a node up to the requested traversal depth."""
    ...