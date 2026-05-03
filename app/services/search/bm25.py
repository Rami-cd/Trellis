from __future__ import annotations
from rank_bm25 import BM25Okapi
from app.schemas.node import CodeNode

def _build_document(node: CodeNode) -> str:
    return (
        f"{node.qualified_name}\n\n"
        f"Summary: {node.summary or ''}\n\n"
        f"{node.raw_source or ''}"
    )

def _tokenize(text: str) -> list[str]:
    return text.lower().split()

class BM25Index:
    def __init__(self) -> None:
        self._index: BM25Okapi | None = None
        self._node_ids: list[str] = []

    def build(self, nodes: list[CodeNode]) -> None:
        self._node_ids = [node.id for node in nodes]
        tokenized = [_tokenize(_build_document(node)) for node in nodes]
        self._index = BM25Okapi(tokenized) if tokenized else None

    def search(self, query: str, top_k: int = 10) -> list[str]:
        if not self.is_built() or top_k <= 0:
            return []
        tokens = _tokenize(query)
        if not tokens:
            return []
        if self._index:
            scores = self._index.get_scores(tokens)
            ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
            return [self._node_ids[i] for i in ranked[:top_k]]
        return []

    def is_built(self) -> bool:
        return self._index is not None