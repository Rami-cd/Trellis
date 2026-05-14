from __future__ import annotations
from app.llm.embedding.base import BaseEmbedder
from app.services.search.bm25 import BM25Index
from app.services.search.vector import VectorSearch

class HybridSearch:
    def __init__(
        self,
        bm25: BM25Index,
        vector: VectorSearch,
        embedder: BaseEmbedder,
    ) -> None:
        self.bm25 = bm25
        self.vector = vector
        self.embedder = embedder

    async def search(
        self,
        query: str,
        repo_id: str,
        top_k: int = 10,
    ) -> list[str]:
        if top_k <= 0:
            return []

        query_embedding = (await self.embedder.embed([query]))[0]

        bm25_results = self.bm25.search(query, top_k=top_k)
        vector_results = await self.vector.search(
            query_embedding,
            repo_id=repo_id,
            top_k=top_k,
        )

        fused_scores: dict[str, float] = {}
        rrf_k = 60

        for results in (bm25_results, vector_results):
            for rank, node_id in enumerate(results):
                fused_scores[node_id] = fused_scores.get(node_id, 0.0) + 1 / (
                    rrf_k + rank
                )

        ranked = sorted(
            fused_scores.items(),
            key=lambda item: item[1],
            reverse=True,
        )
        return [node_id for node_id, _ in ranked[:top_k]]
