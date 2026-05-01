from __future__ import annotations

import argparse
import time
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.db.connection import SessionLocal, engine
from app.db.repository import (
    get_unresolved_edges,
    insert_edges,
    insert_nodes,
    upsert_repository,
)
from app.extractors.python_extractor import PythonExtractor
from app.extractors.resolver.resolver import resolve_call
from app.parsers.parser_registry import ParserRegistry
from app.parsers.python_parser import PythonParser

DEFAULT_REPO_ID = "test_repo"
DEFAULT_DB_RETRIES = 30
DEFAULT_DB_RETRY_DELAY_SECONDS = 2.0

def _discover_project_modules(repo_root: Path) -> set[str]:
    modules: set[str] = set()

    for file_path in repo_root.rglob("*.py"):
        relative_path = file_path.relative_to(repo_root)

        if relative_path.name == "__init__.py":
            parts = relative_path.parent.parts
        else:
            parts = relative_path.with_suffix("").parts

        if parts:
            modules.add(".".join(parts))

    return modules


def _wait_for_database(
    retries: int = DEFAULT_DB_RETRIES,
    delay_seconds: float = DEFAULT_DB_RETRY_DELAY_SECONDS,
) -> None:
    last_error: OperationalError | None = None

    for attempt in range(1, retries + 1):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return
        except OperationalError as exc:
            last_error = exc
            if attempt == retries:
                break
            time.sleep(delay_seconds)

    if last_error is not None:
        raise last_error

def run_pipeline(repo_path: str, repo_id: str = DEFAULT_REPO_ID) -> dict[str, int]:
    repo_root = Path(repo_path).resolve()
    if not repo_root.exists():
        raise FileNotFoundError(f"Repository path does not exist: {repo_root}")
    if not repo_root.is_dir():
        raise NotADirectoryError(f"Repository path is not a directory: {repo_root}")

    registry = ParserRegistry([PythonParser()])
    extractor = PythonExtractor(
        repo=repo_id,
        project_modules=_discover_project_modules(repo_root),
    )

    all_nodes = []
    all_edges = []
    parsed_files = 0

    for file_path in repo_root.rglob("*"):
        if not file_path.is_file():
            continue

        relative_path = file_path.relative_to(repo_root).as_posix()
        parser = registry.get_by_extension(relative_path)
        if parser is None:
            continue

        source = file_path.read_text(encoding="utf-8", errors="replace")
        tree = parser.parse(source, relative_path)
        if tree is None:
            continue

        nodes, edges = extractor.extract(
            tree,
            source.encode("utf-8", errors="replace"),
            relative_path,
        )
        all_nodes.extend(nodes)
        all_edges.extend(edges)
        parsed_files += 1

    _wait_for_database()

    session = SessionLocal()
    try:
        upsert_repository(
            session=session,
            repo_id=repo_id,
            name=repo_root.name,
            path=str(repo_root),
            language="python",
        )
        insert_nodes(session=session, repo_id=repo_id, nodes=all_nodes)
        insert_edges(session=session, edges=all_edges)
        unresolved_edge_ids = [
            edge.id for edge in get_unresolved_edges(session=session, repo_id=repo_id)
        ]
    finally:
        session.close()

    for edge_id in unresolved_edge_ids:
        resolve_call(edge_id, repo_id=repo_id)

    return {
        "files": parsed_files,
        "nodes": len(all_nodes),
        "edges": len(all_edges),
        "unresolved_edges": len(unresolved_edge_ids),
    }


def main() -> int:
    argument_parser = argparse.ArgumentParser()
    argument_parser.add_argument("repo_path")
    argument_parser.add_argument("--repo-id", default=DEFAULT_REPO_ID)
    args = argument_parser.parse_args()

    result = run_pipeline(repo_path=args.repo_path, repo_id=args.repo_id)
    print(
        "Pipeline finished: "
        f"{result['files']} files, "
        f"{result['nodes']} nodes, "
        f"{result['edges']} edges, "
        f"{result['unresolved_edges']} unresolved edges sent to resolver."
    )
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
