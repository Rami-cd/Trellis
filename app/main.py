from __future__ import annotations

import logging
import os
from pathlib import Path

from app.db.connection import SessionLocal
from app.db.repository import (
    fetch_by_repo,
    get_nodes_by_ids,
    get_subgraph,
    insert_edges,
    insert_nodes,
    upsert_repository,
)
from app.extractors.python_extractor import PythonExtractor
from app.extractors.resolver.resolver import resolve_edges
from app.llm.gemini import GeminiLLM
from app.llm.embedding.jina_embedder import JinaEmbedder
from app.llm.summarizer.gemini import GeminiSummarizer
from app.parsers.parser_registry import ParserRegistry
from app.parsers.python_parser import PythonParser
from app.schemas.node import CodeNode, CodeNodeType
from app.services.indexer import Indexer
from app.services.prompt_builder import build_explanation_prompt
from app.services.search.bm25 import BM25Index

logger = logging.getLogger(__name__)

DEFAULT_REPO_PATH = Path(__file__).resolve().parent
REPO_PATH = Path(os.environ.get("TRELLIS_REPO_PATH", str(DEFAULT_REPO_PATH)))
SEARCH_QUERY = "database connection"
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


def _build_repo_id(repo_root: Path) -> str:
    return f"triller_app"


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
            if not file_name.endswith(".py"):
                continue
            python_files.append(current_path / file_name)

    return python_files


def _collect_graph(repo_root: Path, repo_id: str) -> tuple[list[CodeNode], list]:
    parser_registry = ParserRegistry([PythonParser()])
    extractor = PythonExtractor(repo=repo_id)

    nodes = []
    edges = []

    for file_path in _iter_python_files(repo_root):
        relative_path = file_path.relative_to(repo_root).as_posix()
        parser = parser_registry.get_by_extension(relative_path)
        if parser is None:
            continue

        source = file_path.read_text(encoding="utf-8", errors="replace")
        tree = parser.parse(source, relative_path)
        if tree is None:
            continue

        file_nodes, file_edges = extractor.extract(tree, source.encode(), relative_path)
        nodes.extend(file_nodes)
        edges.extend(file_edges)

    return nodes, edges


def _log_top_results(label: str, node_ids: list[str], nodes_by_id: dict[str, CodeNode]) -> None:
    logger.info("%s results (%d)", label, len(node_ids))
    for node_id in node_ids:
        node = nodes_by_id.get(node_id)
        if node is None:
            logger.info("  - %s", node_id)
            continue
        logger.info("  - %s [%s]", node.qualified_name, node.type.value)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    
    # Section 1: choose a small local repo and give this smoke test a fresh repo id.
    repo_root = REPO_PATH.resolve()
    if not repo_root.exists():
        raise FileNotFoundError(f"Repository path does not exist: {repo_root}")
    repo_id = _build_repo_id(repo_root)
    logger.info("Starting smoke test for repo_id=%s at %s", repo_id, repo_root)

    # Section 2: parse Python files, extract nodes/edges, and resolve cross-node links.
    nodes, edges = _collect_graph(repo_root, repo_id)
    resolved, unresolved, edges = resolve_edges(nodes, edges)
    logger.info(
        "Collected %d nodes and %d edges (%d resolved, %d unresolved)",
        len(nodes),
        len(edges),
        resolved,
        unresolved,
    )

    # Section 3: save the extracted graph so later stages can read from the database.
    with SessionLocal() as db:
        upsert_repository(
            db,
            repo_id=repo_id,
            name=repo_root.name,
            path=str(repo_root),
            languages=["python"],
        )
        insert_nodes(db, repo_id, nodes)
        insert_edges(db, edges)
        logger.info("Inserted repository graph into the database")

        # Section 4: run the indexing pass to generate summaries and embeddings.
        # summarizer = GeminiSummarizer()
        embedder = JinaEmbedder()
        # indexer = Indexer(summarizer=summarizer, embedder=embedder, db=db)
        # stats = indexer.run(repo_id=repo_id, nodes=nodes)
        # logger.info("Indexer stats: %s", stats)

        # Section 5: reload indexed nodes and build the in-memory BM25 search index.
        indexed_nodes = fetch_by_repo(db, repo_id)
        searchable_nodes = [
            node
            for node in indexed_nodes
            if node.type in {CodeNodeType.FUNCTION, CodeNodeType.CLASS}
        ]
        indexed_node_lookup = {
            node.id: {
                "id": node.id,
                "qualified_name": node.qualified_name,
                "type": node.type.value,
                "summary": node.summary,
                "raw_source": node.raw_source,
            }
            for node in indexed_nodes
        }
        nodes_by_id = {node.id: node for node in searchable_nodes}

        bm25 = BM25Index()
        bm25.build(searchable_nodes)
        bm25_results = bm25.search(SEARCH_QUERY, top_k=5)
        _log_top_results("BM25", bm25_results, nodes_by_id)

        # Section 6: run vector + hybrid search when the optional runtime dependencies exist.
        try:
            from app.services.search.hybrid import HybridSearch
            from app.services.search.vector import VectorSearch
        except Exception as exc:
            logger.warning("Skipping vector/hybrid search: %s", exc)
            return

        vector = VectorSearch(db)
        hybrid = HybridSearch(bm25=bm25, vector=vector, embedder=embedder)
        hybrid_results = hybrid.search(SEARCH_QUERY, top_k=5)
        _log_top_results("Hybrid", hybrid_results, nodes_by_id)

        gemini = GeminiLLM()
        questions = [
            # tests call graph understanding
            "How does the indexer work end to end?",
            
            # tests inheritance resolution
            "What is the relationship between BaseEmbedder, JinaEmbedder and OllamaEmbedder?",
            
            # tests cross-module call resolution
            "How does hybrid search combine BM25 and vector search results?",
            
            # tests internal method chain understanding
            "How does GeminiSummarizer handle rate limiting and batching?",
            
            # tests graph traversal depth — requires knowing indexer → repository → DB
            "What database operations does the indexer trigger?",
        ]

        for query in questions:
            seed_ids = hybrid.search(query, top_k=5)
            subgraph = get_subgraph(db, seed_ids, depth=2)

            node_index = {
                node["id"]: indexed_node_lookup.get(node["id"], node)
                for node in subgraph["nodes"]
            }
            missing_seed_ids = [node_id for node_id in seed_ids if node_id not in node_index]
            for node in get_nodes_by_ids(db, missing_seed_ids):
                node_index[node["id"]] = indexed_node_lookup.get(node["id"], node)

            seed_set = set(seed_ids)
            seed_nodes = [node_index[node_id] for node_id in seed_ids if node_id in node_index]
            related_nodes = [
                node_index[node["id"]]
                for node in subgraph["nodes"]
                if node["id"] not in seed_set and node["id"] in node_index
            ]

            prompt = build_explanation_prompt(
                query=query,
                seed_nodes=seed_nodes,
                related_nodes=related_nodes,
                edges=subgraph["edges"],
                node_index=node_index,
            )

            answer = gemini.generate(prompt)

            print(f"\n{'=' * 60}")
            print(f"Q: {query}")
            print(f"{'=' * 60}")
            print(answer)

# def count_repo(repo_root: Path) -> None:
#     repo_id = "triller_diagnostic"
#     nodes, edges = _collect_graph(repo_root, repo_id)
#     resolved, unresolved, edges = resolve_edges(nodes, edges)
    
#     from collections import Counter
#     type_counts = Counter(n.type.value for n in nodes)
    
#     print(f"\n=== {repo_root.name} ===")
#     print(f"Total nodes : {len(nodes)}")
#     print(f"Total edges : {len(edges)}")
#     print(f"  resolved  : {resolved}")
#     print(f"  unresolved: {unresolved}")
#     print(f"\nNode breakdown:")
#     for type_name, count in type_counts.most_common():
#         print(f"  {type_name:10} : {count}")
    
#     # add this
#     print(f"\nResolved edges:")
#     for e in edges:
#         if e.target_id:
#             print(f"  {e.source_id[:8]}... → {e.target_ref} [{e.type}]")

if __name__ == "__main__":
    main()
