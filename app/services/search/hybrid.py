from app.services.search.bm25 import BM25Index
from app.services.search.vector import VectorSearch

class HybridSearch:
    def __init__(self, bm25: BM25Index, vector: VectorSearch, embedder):
        ...


    def search(self, query: str, top_k: int = 10) -> list[str]:
        ...