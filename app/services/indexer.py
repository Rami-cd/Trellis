from __future__ import annotations
import logging
from app.db.repository import update_summary, upsert_embedding
from app.llm.embedding.jina_embedder import JinaEmbedder
from app.llm.summarizer.gemini import GeminiSummarizer
from app.schemas.node import CodeNode, CodeNodeType

logger = logging.getLogger(__name__)

def _build_document(node: CodeNode) -> str:
    return f"{node.qualified_name}\n\nSummary: {node.summary or ''}\n\n{node.raw_source or ''}"

class Indexer:
    def __init__(
        self,
        summarizer: GeminiSummarizer,
        embedder: JinaEmbedder,
        db,
    ) -> None:
        self.summarizer = summarizer
        self.embedder = embedder
        self.db = db

    def run(self, repo_id: str, nodes: list[CodeNode]) -> dict:
        logger.info("Starting indexing for repo_id=%s", repo_id)
        eligible_nodes = [
            node
            for node in nodes
            if node.type != CodeNodeType.MODULE and node.raw_source is not None
        ]

        logger.info(
            "Fetched %d nodes for repo_id=%s; %d eligible for indexing",
            len(nodes),
            repo_id,
            len(eligible_nodes),
        )

        summaries = self.summarizer.summarize_batch(eligible_nodes)
        summaries_generated = 0
        for node in eligible_nodes:
            summary = summaries.get(node.id)
            if summary is None:
                continue
            update_summary(self.db, node.id, summary)
            node.summary = summary
            summaries_generated += 1

        self.db.commit()
        logger.info(
            "Stored %d summaries for repo_id=%s",
            summaries_generated,
            repo_id,
        )

        node_docs = [(node.id, _build_document(node)) for node in eligible_nodes]
        embeddings_stored = 0

        if node_docs:
            docs = [doc for _, doc in node_docs]
            vectors = self.embedder.embed(docs)

            if len(vectors) != len(node_docs):
                logger.warning(
                    "Embedding count mismatch for repo_id=%s: expected=%d actual=%d",
                    repo_id,
                    len(node_docs),
                    len(vectors),
                )

            for index, (node_id, doc) in enumerate(node_docs):
                if index >= len(vectors):
                    logger.warning(
                        "Missing embedding vector for node_id=%s; skipping",
                        node_id,
                    )
                    continue

                vector = vectors[index]
                try:
                    with self.db.begin_nested():
                        upsert_embedding(self.db, node_id, doc, vector)
                    embeddings_stored += 1
                except Exception:
                    logger.warning(
                        "Failed to store embedding for node_id=%s",
                        node_id,
                        exc_info=True,
                    )

        self.db.commit()
        logger.info(
            "Stored %d embeddings for repo_id=%s",
            embeddings_stored,
            repo_id,
        )

        return {
            "nodes_processed": len(eligible_nodes),
            "summaries_generated": summaries_generated,
            "embeddings_stored": embeddings_stored,
        }