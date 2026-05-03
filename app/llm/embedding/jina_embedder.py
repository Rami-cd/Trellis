import logging
import os
import time

import httpx

from app.llm.embedding.base import BaseEmbedder

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
MODEL = "unclemusclez/jina-embeddings-v2-base-code:q4"
EMBED_BATCH_SIZE = int(os.environ.get("EMBED_BATCH_SIZE", "8"))
EMBED_TIMEOUT_SECONDS = float(os.environ.get("EMBED_TIMEOUT_SECONDS", "180"))
EMBED_MAX_RETRIES = int(os.environ.get("EMBED_MAX_RETRIES", "3"))
EMBED_RETRY_BACKOFF_SECONDS = float(
    os.environ.get("EMBED_RETRY_BACKOFF_SECONDS", "5")
)


def _chunked(texts: list[str], batch_size: int) -> list[list[str]]:
    return [texts[index : index + batch_size] for index in range(0, len(texts), batch_size)]


def _should_retry(exc: Exception) -> bool:
    if isinstance(exc, (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code >= 500
    return False


def _split_in_half(texts: list[str]) -> tuple[list[str], list[str]]:
    midpoint = max(1, len(texts) // 2)
    return texts[:midpoint], texts[midpoint:]

class JinaEmbedder(BaseEmbedder):
    def _embed_batch(
        self,
        client: httpx.Client,
        texts: list[str],
        batch_label: str,
    ) -> list[list[float]]:
        if not texts:
            return []

        for attempt in range(1, EMBED_MAX_RETRIES + 1):
            try:
                response = client.post(
                    f"{OLLAMA_BASE_URL}/api/embed",
                    json={"model": MODEL, "input": texts},
                )
                response.raise_for_status()

                embeddings = response.json().get("embeddings", [])
                if len(embeddings) != len(texts):
                    raise ValueError(
                        "Embedding response size mismatch: "
                        f"expected={len(texts)} actual={len(embeddings)}"
                    )

                return embeddings
            except Exception as exc:
                if not _should_retry(exc):
                    raise

                if len(texts) > 1:
                    left, right = _split_in_half(texts)
                    logger.warning(
                        "Embedding %s timed out for %d texts on attempt %d/%d. "
                        "Splitting into %d and %d texts.",
                        batch_label,
                        len(texts),
                        attempt,
                        EMBED_MAX_RETRIES,
                        len(left),
                        len(right),
                    )
                    return self._embed_batch(client, left, f"{batch_label}a") + self._embed_batch(
                        client,
                        right,
                        f"{batch_label}b",
                    )

                if attempt == EMBED_MAX_RETRIES:
                    raise

                wait_seconds = EMBED_RETRY_BACKOFF_SECONDS * attempt
                logger.warning(
                    "Embedding %s failed for a single text on attempt %d/%d: %s. "
                    "Retrying in %.1fs.",
                    batch_label,
                    attempt,
                    EMBED_MAX_RETRIES,
                    exc,
                    wait_seconds,
                )
                time.sleep(wait_seconds)

        raise RuntimeError(f"Embedding failed unexpectedly for {batch_label}")

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        all_embeddings: list[list[float]] = []
        batches = _chunked(texts, max(1, EMBED_BATCH_SIZE))

        with httpx.Client(timeout=EMBED_TIMEOUT_SECONDS) as client:
            for batch_index, batch in enumerate(batches, start=1):
                batch_label = f"batch {batch_index}/{len(batches)}"
                all_embeddings.extend(self._embed_batch(client, batch, batch_label))

        return all_embeddings
