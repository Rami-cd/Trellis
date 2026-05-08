from __future__ import annotations
import logging
import os

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repository import update_summary, upsert_embedding
from app.llm.embedding.jina_embedder import JinaEmbedder
from app.llm.summarizer.base import BaseSummarizer
from app.schemas.node import CodeNode, CodeNodeType

logger = logging.getLogger(__name__)
MAX_EMBED_DOCUMENT_CHARS = int(os.environ.get("MAX_EMBED_DOCUMENT_CHARS", "6000"))


def _build_document(node: CodeNode) -> str:
    prefix = f"{node.qualified_name}\n\nSummary: {node.summary or ''}\n\n"
    raw_source = node.raw_source or ""
    remaining_chars = max(0, MAX_EMBED_DOCUMENT_CHARS - len(prefix))
    return prefix + raw_source[:remaining_chars]


class Indexer:
    def __init__(
        self,
        summarizer: BaseSummarizer | None,
        embedder: JinaEmbedder,
        db: AsyncSession,
    ) -> None:
        self.summarizer = summarizer
        self.embedder = embedder
        self.db = db

    async def run(self, repo_id: str, nodes: list[CodeNode]) -> dict:
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

        if self.summarizer:
            # NOTE: flag summarize_batch as async if BaseSummarizer is not yet async
            summaries = await self.summarizer.summarize_batch(eligible_nodes)
            summaries_generated = 0

            for node in eligible_nodes:
                summary = summaries.get(node.id)
                if summary is None:
                    continue
                await update_summary(self.db, node.id, summary)
                node.summary = summary
                summaries_generated += 1

            # Commit all summaries together atomically
            await self.db.commit()
            logger.info(
                "Stored %d summaries for repo_id=%s",
                summaries_generated,
                repo_id,
            )
        else:
            summaries_generated = 0
            logger.info("No summarizer configured; skipping summary generation")

        node_docs = [(node.id, _build_document(node)) for node in eligible_nodes]
        embeddings_stored = 0

        if node_docs:
            docs = [doc for _, doc in node_docs]
            # NOTE: flag embed as async if JinaEmbedder is not yet async
            vectors = await self.embedder.embed(docs)

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
                    async with self.db.begin_nested():
                        await upsert_embedding(self.db, node_id, doc, vector)
                    embeddings_stored += 1
                except Exception:
                    logger.warning(
                        "Failed to store embedding for node_id=%s",
                        node_id,
                        exc_info=True,
                    )

        # Commit all successfully saved embeddings together
        await self.db.commit()
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