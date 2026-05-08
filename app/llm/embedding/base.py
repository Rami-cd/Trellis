from abc import ABC, abstractmethod

class BaseEmbedder(ABC):
    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        ...