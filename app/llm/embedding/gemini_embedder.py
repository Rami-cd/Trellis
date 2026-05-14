from __future__ import annotations

import asyncio
import logging
import os
import random
from typing import AsyncIterator

import httpx

from app.llm.embedding.base import BaseEmbedder
from app.settings.config import LLM_CONFIG

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config Extraction
# ---------------------------------------------------------------------------

_EMBED_CFG = LLM_CONFIG.get("embedding", {})
_GEMINI_EMBED_CFG = _EMBED_CFG.get("gemini", {})
_GEMINI_GEN_CFG = LLM_CONFIG.get("gemini", {})

# Model choice: text-embedding-004 is the standard free-tier choice.
MODEL: str = _GEMINI_EMBED_CFG.get("model_name", "gemini-embedding-001")
TASK_TYPE: str = _GEMINI_EMBED_CFG.get("task_type", "RETRIEVAL_DOCUMENT")
# Most local DBs for RAG use 768 or 1536. 
DIMENSIONS: int = int(_GEMINI_EMBED_CFG.get("dimensions", 768))

BATCH_SIZE: int = min(int(_GEMINI_EMBED_CFG.get("batch_size", 100)), 100)
MAX_RETRIES: int = int(_GEMINI_GEN_CFG.get("max_retries", 3))

_RATE_CFG = _GEMINI_GEN_CFG.get("rate_limit", {})
REQUESTS_PER_WINDOW: int = int(_RATE_CFG.get("requests_per_window", 15))
RATE_WINDOW_SLEEP_SECONDS: float = float(_RATE_CFG.get("sleep_seconds", 60))
RETRY_WAIT_SECONDS: float = float(_RATE_CFG.get("retry_wait_seconds", 65))

_API_KEY: str = os.environ.get("GEMINI_API_KEY", "")
_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
_HTTP_TIMEOUT = 60.0

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _chunked(texts: list[str], size: int) -> list[list[str]]:
    return [texts[i : i + size] for i in range(0, len(texts), size)]

def _is_rate_limit(exc: Exception) -> bool:
    return isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 429

def _is_retryable(exc: Exception) -> bool:
    if isinstance(exc, (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in {429, 500, 502, 503, 504}
    return False

# ---------------------------------------------------------------------------
# Embedder
# ---------------------------------------------------------------------------

class GeminiEmbedder(BaseEmbedder):
    """
    Optimized Gemini Embedder for Free Tier usage.
    Handles partial persistence and dimensionality control.
    """

    async def _embed_single_batch(
        self,
        client: httpx.AsyncClient,
        texts: list[str],
        batch_label: str,
    ) -> list[list[float]]:
        if not texts:
            return []

        # Added outputDimensionality to ensure the vectors fit your DB schema
        payload = {
            "requests": [
                {
                    "model": f"models/{MODEL}",
                    "content": {"parts": [{"text": t}]},
                    "taskType": TASK_TYPE,
                    "outputDimensionality": DIMENSIONS
                }
                for t in texts
            ]
        }
        
        # Ensure the URL is correctly formed
        url = f"{_BASE_URL}/models/{MODEL}:batchEmbedContents?key={_API_KEY}"

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = await client.post(url, json=payload)
                response.raise_for_status()

                embeddings_raw = response.json().get("embeddings", [])
                vectors = [item["values"] for item in embeddings_raw]

                if len(vectors) != len(texts):
                    raise ValueError(f"Size mismatch: {len(texts)} vs {len(vectors)}")

                return vectors

            except Exception as exc:
                if not _is_retryable(exc):
                    logger.error("Non-retryable error on %s: %s", batch_label, exc)
                    raise

                if attempt == MAX_RETRIES:
                    raise

                # Use jitter to avoid 'thundering herd' on free tier limits
                wait = RETRY_WAIT_SECONDS if _is_rate_limit(exc) else (attempt * 5.0 + random.uniform(0, 1))
                logger.warning("Retrying %s (Attempt %d/%d) in %.1fs", batch_label, attempt, MAX_RETRIES, wait)
                await asyncio.sleep(wait)

        raise RuntimeError("Embedding loop failure")

    async def embed_iter(
        self,
        texts: list[str],
    ) -> AsyncIterator[tuple[list[str], list[list[float]]]]:
        if not texts:
            return

        batches = _chunked(texts, BATCH_SIZE)
        requests_this_window = 0

        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            for idx, batch in enumerate(batches, start=1):
                if requests_this_window > 0 and requests_this_window % REQUESTS_PER_WINDOW == 0:
                    logger.info("Rate limit cooldown: sleeping %.0fs", RATE_WINDOW_SLEEP_SECONDS)
                    await asyncio.sleep(RATE_WINDOW_SLEEP_SECONDS)

                vectors = await self._embed_single_batch(client, batch, f"batch {idx}")
                requests_this_window += 1
                yield batch, vectors

    async def embed(self, texts: list[str]) -> list[list[float]]:
        all_vectors: list[list[float]] = []
        async for _, vectors in self.embed_iter(texts):
            all_vectors.extend(vectors)
        return all_vectors