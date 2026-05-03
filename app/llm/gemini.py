from __future__ import annotations
import os
import time
import logging
from dotenv import load_dotenv
from google import genai
from google.genai.errors import APIError
from app.llm.base import BaseLLM

load_dotenv()

logger = logging.getLogger(__name__)

RATE_LIMIT_WAIT = 65
MAX_RETRIES = 3

class GeminiLLM(BaseLLM):

    def __init__(self) -> None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set in environment.")

        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.5-flash-lite"

    def generate(self, prompt: str) -> str:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                )
                if not response or not response.text:
                    return ""
                return response.text.strip()
            except APIError as e:
                if e.code != 429:
                    raise
                if attempt == MAX_RETRIES:
                    logger.error("Rate limit hit too many times; giving up.")
                    raise
                wait = RATE_LIMIT_WAIT * attempt
                logger.warning(f"Rate limit hit; waiting {wait}s before retry {attempt + 1}/{MAX_RETRIES}...")
                time.sleep(wait)

        return ""