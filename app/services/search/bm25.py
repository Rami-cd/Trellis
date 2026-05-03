from app.schemas.node import CodeNode

class BM25Index:
    def __init__(self): ...
    def build(self, nodes: list[CodeNode]) -> None:
        ...


    def search(self, query: str, top_k: int = 10) -> list[str]:
        ...