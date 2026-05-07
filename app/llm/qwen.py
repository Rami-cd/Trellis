from __future__ import annotations
import logging
import time
import requests
from app.llm.base import BaseLLM

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = "http://localhost:11434"
MODEL_NAME = "qwen2.5-coder:7b-instruct"

MAX_RETRIES = 3
RETRY_WAIT = 5


class QwenLLM(BaseLLM):
    def __init__(self) -> None:
        self.base_url = OLLAMA_BASE_URL
        self.model = MODEL_NAME
        self._session = requests.Session()

    def generate(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = self._session.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    timeout=120,
                )
                response.raise_for_status()
                data = response.json()
                return data.get("response", "").strip()

            except requests.exceptions.ConnectionError as e:
                if attempt == MAX_RETRIES:
                    logger.error("Ollama server unreachable after %d attempts.", MAX_RETRIES)
                    raise
                logger.warning(
                    "Connection error (attempt %d/%d): %s — retrying in %ds...",
                    attempt, MAX_RETRIES, e, RETRY_WAIT,
                )
                time.sleep(RETRY_WAIT)

            except requests.exceptions.HTTPError as e:
                logger.error("HTTP error from Ollama: %s", e)
                raise

            except requests.exceptions.Timeout:
                if attempt == MAX_RETRIES:
                    logger.error("Ollama request timed out after %d attempts.", MAX_RETRIES)
                    raise
                logger.warning(
                    "Timeout (attempt %d/%d) — retrying in %ds...",
                    attempt, MAX_RETRIES, RETRY_WAIT,
                )
                time.sleep(RETRY_WAIT)

        return ""