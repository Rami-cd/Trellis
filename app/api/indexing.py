from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.repository import _get_repo_or_404
from app.auth.router import current_active_user
from app.auth.user import User
from app.db.connection import get_session
from app.db.repository import fetch_by_repo, insert_edges, insert_nodes
from app.extractors.python_extractor import PythonExtractor
from app.extractors.resolver.resolver import resolve_edges
from app.llm.embedding.jina_embedder import JinaEmbedder
from app.parsers.parser_registry import ParserRegistry
from app.parsers.python_parser import PythonParser
from app.services.indexer import Indexer

from typing import AsyncGenerator

router = APIRouter(prefix="/repositories", tags=["indexing"])

IGNORED_DIR_NAMES = {
    "__pycache__",
    ".git",
    ".hg",
    ".idea",
    ".mypy_cache",
    ".nox",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    ".vscode",
    "build",
    "dist",
    "env",
    "htmlcov",
    "node_modules",
    "venv",
}

def _iter_python_files(repo_root: Path) -> list[Path]:
    python_files: list[Path] = []

    for current_root, dir_names, file_names in os.walk(repo_root):
        dir_names[:] = sorted(
            dir_name
            for dir_name in dir_names
            if dir_name not in IGNORED_DIR_NAMES
        )

        current_path = Path(current_root)
        for file_name in sorted(file_names):
            if not file_name.endswith((".py", ".pyw")):
                continue
            python_files.append(current_path / file_name)

    return python_files


@router.post("/{repo_id}/index")
async def index_repository(
    repo_id: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    repo = await _get_repo_or_404(repo_id, user, session)

    async def stream() -> AsyncGenerator[str, None]:
        try:
            repo_root = Path(repo["path"]).resolve()
            if not repo_root.exists():
                yield f"error: repository path does not exist: {repo_root}\n"
                return

            parser_registry = ParserRegistry([PythonParser()])
            extractor = PythonExtractor(repo=repo_id)

            python_files = _iter_python_files(repo_root)
            yield f"files found: {len(python_files)}\n"

            nodes = []
            edges = []

            for file_path in python_files:
                relative_path = file_path.relative_to(repo_root).as_posix()
                parser = parser_registry.get_by_extension(relative_path)
                if parser is None:
                    continue

                source = file_path.read_text(encoding="utf-8", errors="replace")
                tree = parser.parse(source, relative_path)
                if tree is None:
                    continue

                file_nodes, file_edges = extractor.extract(
                    tree,
                    source.encode("utf-8", errors="replace"),
                    relative_path,
                )
                nodes.extend(file_nodes)
                edges.extend(file_edges)

            resolved, unresolved, edges = resolve_edges(nodes, edges)
            yield (
                f"nodes/edges: nodes={len(nodes)} "
                f"edges={len(edges)} resolved={resolved} unresolved={unresolved}\n"
            )

            await insert_nodes(session, repo_id, nodes)
            await insert_edges(session, edges)
            yield "database: nodes and edges upserted\n"

            stored_nodes = await fetch_by_repo(session, repo_id)
            indexer = Indexer(
                summarizer=None,
                embedder=JinaEmbedder(),
                db=session,
            )
            stats = await indexer.run(repo_id=repo_id, nodes=stored_nodes)
            yield (
                "embedding stats: "
                f"nodes_processed={stats['nodes_processed']} "
                f"summaries_generated={stats['summaries_generated']} "
                f"embeddings_stored={stats['embeddings_stored']}\n"
            )

            await session.execute(
                text("""
                    UPDATE repositories
                    SET indexed_at = NOW()
                    WHERE id = :repo_id
                """),
                {"repo_id": repo_id},
            )
            await session.commit()

            yield "done\n"
        except Exception as exc:
            yield f"error: {exc}\n"
            return

    return StreamingResponse(stream(), media_type="text/plain")