from __future__ import annotations
import json
from sqlalchemy import text

class VectorSearch:
    def __init__(self, db) -> None:
        self.db = db

    def search(self, query_embedding: list[float], top_k: int = 10) -> list[str]:
        if not query_embedding or top_k <= 0:
            return []

        rows = self.db.execute(
            text("""
                SELECT node_id
                FROM code_embeddings
                ORDER BY embedding <=> CAST(:embedding AS vector)
                LIMIT :top_k
            """),
            {
                "embedding": json.dumps(query_embedding),
                "top_k": top_k,
            }
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
