import os
import httpx
from app.llm.embedding.base import BaseEmbedder

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
MODEL = "nomic-embed-text"

class OllamaEmbedder(BaseEmbedder):

    def embed(self, texts: list[str]) -> list[list[float]]:
        response = httpx.post(
            f"{OLLAMA_BASE_URL}/api/embed",
            json={"model": MODEL, "input": texts},
            timeout=60.0,
        )
        response.raise_for_status()
        return response.json()["embeddings"]