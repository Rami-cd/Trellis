from __future__ import annotations
import json
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

class VectorSearch:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def search(
        self,
        query_embedding: list[float],
        repo_id: str,
        top_k: int = 10,
    ) -> list[str]:
        if not query_embedding or top_k <= 0:
            return []

        rows = (
            await self.db.execute(
                text("""
                    SELECT ce.node_id
                    FROM code_embeddings ce
                    JOIN code_nodes cn ON cn.id = ce.node_id
                    WHERE cn.repo_id = :repo_id
                    ORDER BY ce.embedding <=> CAST(:embedding AS vector)
                    LIMIT :top_k
                """),
                {
                    "repo_id": repo_id,
                    "embedding": json.dumps(query_embedding),
                    "top_k": top_k,
                },
            )
        ).fetchall()

        node_ids: list[str] = []
        seen: set[str] = set()
        for row in rows:
            node_id = row[0]
            if node_id in seen:
                continue
            seen.add(node_id)
            node_ids.append(node_id)

        return node_ids
