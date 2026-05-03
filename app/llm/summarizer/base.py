from abc import ABC, abstractmethod
from app.schemas.node import CodeNode

class BaseSummarizer(ABC):
    @abstractmethod
    def summarize_batch(self, nodes: list[CodeNode]) -> dict[str, str]:
        ...