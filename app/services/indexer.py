from __future__ import annotations
import logging
import os

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repository import (
    delete_nodes,
    fetch_by_repo,
    get_repo_node_content_hashes,
    insert_edges,
    insert_nodes,
    update_summary,
    upsert_embedding,
    get_nodes_with_embeddings
)
from app.llm.embedding.jina_embedder import EMBED_BATCH_SIZE
from app.llm.embedding.gemini_embedder import BaseEmbedder
from app.llm.summarizer.base import BaseSummarizer
from app.schemas.edge import CodeEdge
from app.schemas.node import CodeNode, CodeNodeType

logger = logging.getLogger(__name__)
MAX_EMBED_DOCUMENT_CHARS = int(os.environ.get("MAX_EMBED_DOCUMENT_CHARS", "6000"))
SUMMARY_BATCH_SIZE = int(os.environ.get("SUMMARY_BATCH_SIZE", "24"))


def _build_document(node: CodeNode) -> str:
    prefix = f"{node.qualified_name}\n\nSummary: {node.summary or ''}\n\nComments: {node.attributes.get('comments', '')}\n\n"
    raw_source = node.raw_source or ""
    remaining_chars = max(0, MAX_EMBED_DOCUMENT_CHARS - len(prefix))
    return prefix + raw_source[:remaining_chars]


class Indexer:
    def __init__(
        self,
        summarizer: BaseSummarizer | None,
        embedder: BaseEmbedder,
        db: AsyncSession,
    ) -> None:
        self.summarizer = summarizer
        self.embedder = embedder
        self.db = db

    async def run(
        self,
        repo_id: str,
        nodes: list[CodeNode],
        edges: list[CodeEdge],
    ) -> dict[str, int]:
        logger.info("Starting indexing for repo_id=%s", repo_id)
        stored_nodes = await get_repo_node_content_hashes(self.db, repo_id)
        stored_ids = set(stored_nodes.keys())
        extracted_ids = {node.id for node in nodes}

        new_node_ids: set[str] = set()
        changed_node_ids: set[str] = set()
        unchanged_nodes = 0

        # ====================================================
        # Classify nodes
        # ====================================================

        for node in nodes:
            existing = stored_nodes.get(node.id)
            if existing is None:
                new_node_ids.add(node.id)
                continue
            if existing["content_hash"] != node.content_hash:
                changed_node_ids.add(node.id)
                continue
            unchanged_nodes += 1

        logger.info(
            "Classified extracted nodes for repo_id=%s: new=%d changed=%d unchanged=%d",
            repo_id,
            len(new_node_ids),
            len(changed_node_ids),
            unchanged_nodes,
        )

        # ====================================================
        # Persist nodes and edges
        # ====================================================

        await insert_nodes(self.db, repo_id, nodes)
        await insert_edges(self.db, edges)
        logger.info(
            "Upserted extracted graph for repo_id=%s: nodes=%d edges=%d",
            repo_id,
            len(nodes),
            len(edges),
        )

        # ====================================================
        # Delete orphans
        # ====================================================

        orphan_ids = list(stored_ids - extracted_ids)
        if orphan_ids:
            await delete_nodes(self.db, orphan_ids)
            logger.info(
                "Deleted orphan nodes for repo_id=%s: count=%d",
                repo_id,
                len(orphan_ids),
            )
        else:
            logger.info("No orphan nodes to delete for repo_id=%s", repo_id)

        # ====================================================
        # Fetch current DB state (authoritative after upsert)
        # ====================================================

        current_nodes = await fetch_by_repo(self.db, repo_id)
        current_nodes_by_id: dict[str, CodeNode] = {node.id: node for node in current_nodes}

        changed_new_ids = new_node_ids | changed_node_ids

        # Nodes needing a summary: new, changed, or unchanged-but-summary-missing.
        # Filter out MODULE nodes and nodes with no raw source since we can't summarize those.
        summary_eligible_nodes = [
            current_nodes_by_id[node.id]
            for node in nodes
            if (
                (
                    node.id in changed_new_ids
                    or current_nodes_by_id.get(node.id) is not None
                    and current_nodes_by_id[node.id].summary is None
                )
                and (current_node := current_nodes_by_id.get(node.id)) is not None
                and current_node.type != CodeNodeType.MODULE
                and current_node.raw_source is not None
            )
        ]

        unchanged_missing_summary_ids = {
            node.id
            for node in summary_eligible_nodes
            if node.id not in changed_new_ids
        }

        logger.info(
            "%d nodes require reindexing and %d unchanged nodes are missing summaries "
            "for repo_id=%s; %d eligible for summarization after filtering MODULE/empty",
            len(changed_new_ids),
            len(unchanged_missing_summary_ids),
            repo_id,
            len(summary_eligible_nodes),
        )

        # ====================================================
        # Generate summaries
        #
        # Summaries are committed after each batch so partial progress is preserved.
        # If a batch fails, we roll back only that batch and continue with the next.
        # ====================================================

        summaries_generated = 0
        if self.summarizer and summary_eligible_nodes:
            for start in range(0, len(summary_eligible_nodes), SUMMARY_BATCH_SIZE):
                batch = summary_eligible_nodes[start:start + SUMMARY_BATCH_SIZE]
                try:
                    summaries = await self.summarizer.summarize_batch(batch)

                    for node in batch:
                        summary = summaries.get(node.id)
                        if summary is None:
                            continue
                        await update_summary(self.db, node.id, summary)
                        current_nodes_by_id[node.id].summary = summary
                        summaries_generated += 1

                    await self.db.commit()
                    logger.info(
                        "Committed summaries for repo_id=%s batch_start=%d batch_size=%d",
                        repo_id,
                        start,
                        len(batch),
                    )

                except Exception:
                    logger.error(
                        "Summary batch failed for repo_id=%s batch_start=%d; preserving prior batches and continuing.",
                        repo_id,
                        start,
                        exc_info=True,
                    )
                    await self.db.rollback()

            logger.info(
                "Stored %d summaries for repo_id=%s",
                summaries_generated,
                repo_id,
            )
        elif not self.summarizer:
            logger.info("No summarizer configured; skipping summary generation")
        else:
            logger.info("All nodes already have summaries for repo_id=%s; proceeding to embedding", repo_id)

        # ====================================================
        # Determine which nodes need embeddings
        #
        # Policy:
        #   - new nodes          → always embed
        #   - changed nodes      → always embed (content changed, vector is stale)
        #   - unchanged nodes    → embed only if embedding is missing
        #
        # All candidates must pass the same MODULE / raw_source filter used above,
        # and must have a summary (either pre-existing or just generated) so the
        # embedding document is meaningful.
        # ====================================================

        nodes_with_embeddings: set[str] = await get_nodes_with_embeddings(self.db, repo_id)

        # Pre-compute sets once to keep the list comprehension O(n).
        all_node_ids = {node.id for node in nodes}

        nodes_to_embed: list[CodeNode] = []
        for node_id in all_node_ids:
            current = current_nodes_by_id.get(node_id)
            if current is None:
                continue  # orphan already deleted
            if current.type == CodeNodeType.MODULE:
                continue  # modules are never embedded
            if current.raw_source is None:
                continue  # nothing to embed
            if current.summary is None:
                continue  # do not embed nodes without summaries

            is_new_or_changed = node_id in changed_new_ids
            is_missing_embedding = node_id not in nodes_with_embeddings

            if is_new_or_changed or is_missing_embedding:
                nodes_to_embed.append(current)

        logger.info(
            "Prepared %d nodes for embedding for repo_id=%s",
            len(nodes_to_embed),
            repo_id,
        )

        # ====================================================
        # Generate and store embeddings
        # ====================================================

        node_docs = [(node.id, _build_document(node)) for node in nodes_to_embed]
        embeddings_stored = 0
        batch_size = EMBED_BATCH_SIZE

        if node_docs:
            try:
                for i in range(0, len(node_docs), batch_size):
                    batch = node_docs[i:i + batch_size]

                    try:
                        docs = [doc for _, doc in batch]
                        vectors = await self.embedder.embed(docs)

                        if len(vectors) != len(batch):
                            logger.warning(
                                "Embedding count mismatch for repo_id=%s: expected=%d actual=%d",
                                repo_id,
                                len(batch),
                                len(vectors),
                            )

                        for index, (node_id, doc) in enumerate(batch):
                            if index >= len(vectors):
                                logger.warning(
                                    "Missing embedding vector for node_id=%s; skipping",
                                    node_id,
                                )
                                continue

                            vector = vectors[index]

                            try:
                                async with self.db.begin_nested():
                                    await upsert_embedding(
                                        self.db,
                                        node_id,
                                        doc,
                                        vector,
                                    )

                                embeddings_stored += 1

                            except Exception:
                                logger.warning(
                                    "Failed to store embedding for node_id=%s",
                                    node_id,
                                    exc_info=True,
                                )

                        await self.db.commit()

                    except Exception:
                        logger.warning(
                            "Embedding batch failed for repo_id=%s batch_start=%d",
                            repo_id,
                            i,
                            exc_info=True,
                        )

            finally:
                logger.info(
                    "Stored %d embeddings for repo_id=%s",
                    embeddings_stored,
                    repo_id,
                )

        return {
            "new": len(new_node_ids),
            "changed": len(changed_node_ids),
            "unchanged": unchanged_nodes,
            "orphans_deleted": len(orphan_ids),
            "summaries_generated": summaries_generated,
            "embeddings_stored": embeddings_stored,
        }