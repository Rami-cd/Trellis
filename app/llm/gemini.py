from __future__ import annotations
import os
import time
import logging
from collections.abc import Iterator
from dotenv import load_dotenv
from google import genai
from google.genai.errors import APIError
from app.llm.base import BaseLLM
from app.llm.gemini_rate_limiter import wait_for_gemini_rate_limit
from app.settings.config import LLM_CONFIG

load_dotenv()

logger = logging.getLogger(__name__)

GEMINI_CONFIG = LLM_CONFIG.get("gemini", {})
RATE_LIMIT_WAIT = GEMINI_CONFIG["rate_limit"]["retry_wait_seconds"]
MAX_RETRIES = GEMINI_CONFIG["max_retries"]


def _is_retryable_api_error(error: APIError) -> bool:
    return error.code == 429 or error.code >= 500

class GeminiLLM(BaseLLM):

    def __init__(self) -> None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set in environment.")

        self.client = genai.Client(api_key=api_key)
        self.model = GEMINI_CONFIG["model_name"]

    def generate(self, prompt: str) -> str:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                wait_for_gemini_rate_limit()
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                )
                if not response or not response.text:
                    return ""
                return response.text.strip()
            except APIError as e:
                if not _is_retryable_api_error(e):
                    raise
                if attempt == MAX_RETRIES:
                    logger.error("Gemini request failed too many times with retryable errors; giving up.")
                    raise
                wait = RATE_LIMIT_WAIT * attempt
                logger.warning(
                    "Gemini request failed with status %s; waiting %ss before retry %s/%s...",
                    e.code,
                    wait,
                    attempt + 1,
                    MAX_RETRIES,
                )
                time.sleep(wait)

        return ""

    def generate_stream(self, prompt: str) -> Iterator[str]:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                wait_for_gemini_rate_limit()
                response = self.client.models.generate_content_stream(
                    model=self.model,
                    contents=prompt,
                )
                for chunk in response:
                    if chunk and chunk.text:
                        yield chunk.text
                return
            except APIError as e:
                if not _is_retryable_api_error(e):
                    raise
                if attempt == MAX_RETRIES:
                    logger.error("Gemini streaming request failed too many times with retryable errors; giving up.")
                    raise
                wait = RATE_LIMIT_WAIT * attempt
                logger.warning(
                    "Gemini streaming request failed with status %s; waiting %ss before retry %s/%s...",
                    e.code,
                    wait,
                    attempt + 1,
                    MAX_RETRIES,
                )
                time.sleep(wait)
