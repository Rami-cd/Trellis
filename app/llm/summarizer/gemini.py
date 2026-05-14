import asyncio
import json
import logging
import os
import time
from pathlib import Path
from google import genai
from google.genai import types
from google.genai.errors import APIError
from jinja2 import Environment, FileSystemLoader, select_autoescape
from app.llm.gemini_rate_limiter import wait_for_gemini_rate_limit
from app.llm.summarizer.base import BaseSummarizer
from app.schemas.node import CodeNode, CodeNodeType
from app.settings.config import LLM_CONFIG

logger = logging.getLogger(__name__)

GEMINI_SUMMARIZER_CONFIG = LLM_CONFIG.get("summarizer", {}).get("gemini", {})
GEMINI_CONFIG = LLM_CONFIG.get("gemini", {})

MAX_TOKENS_PER_BATCH = GEMINI_SUMMARIZER_CONFIG["max_tokens_per_batch"]
MAX_NODES_PER_BATCH = GEMINI_SUMMARIZER_CONFIG["max_nodes_per_batch"]
CHARS_PER_TOKEN = GEMINI_SUMMARIZER_CONFIG["chars_per_token"]
RATE_LIMIT_WAIT = GEMINI_CONFIG["rate_limit"]["retry_wait_seconds"]
MAX_RATE_LIMIT_RETRIES = GEMINI_SUMMARIZER_CONFIG["max_rate_limit_retries"]


def _is_retryable_api_error(error: APIError) -> bool:
    return error.code == 429 or error.code >= 500

PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"

jinja_env = Environment(
    loader=FileSystemLoader(PROMPTS_DIR),
    trim_blocks=True,
    lstrip_blocks=True,
    autoescape=select_autoescape(enabled_extensions=()),
)

PROMPT_TEMPLATE = jinja_env.get_template("summary_prompt.j2")


def _estimate_tokens(text: str) -> int:
    return (len(text) + CHARS_PER_TOKEN - 1) // CHARS_PER_TOKEN

def _build_meta(node: CodeNode) -> str:
    if node.type == CodeNodeType.FUNCTION:
        args = dict(node.attributes.get("args", {}))
        returns = node.attributes.get("returns", "None")
        return f"Args: {args} | Returns: {returns}"

    if node.type == CodeNodeType.CLASS:
        bases = list(node.attributes.get("bases", []))
        return f"Inherits from: {bases if bases else 'nothing'}"

    return ""

def _prepare_node(node: CodeNode) -> dict:
    return {
        "id": node.id,
        "qualified_name": node.qualified_name,
        "type": node.type.value,
        "meta": _build_meta(node),
        "raw_source": node.raw_source,
    }


def _render_prompt(nodes: list[dict]) -> str:
    return PROMPT_TEMPLATE.render(nodes=nodes)

EMPTY_PROMPT = _render_prompt([])
PROMPT_OVERHEAD_TOKENS = _estimate_tokens(EMPTY_PROMPT)

def _estimate_node_tokens(node: CodeNode, index: int) -> int:
    prepared = _prepare_node(node)

    block = f"""
        ### NODE {index}
        ID: {prepared["id"]}
        Name: {prepared["qualified_name"]}
        Type: {prepared["type"]}

        Meta: {prepared["meta"]}

        Code:
        {prepared["raw_source"]}
    """

    return _estimate_tokens(block)

def _make_batches(nodes: list[CodeNode]) -> list[list[CodeNode]]:
    batches: list[list[CodeNode]] = []

    current_batch: list[CodeNode] = []
    current_tokens = PROMPT_OVERHEAD_TOKENS

    for index, node in enumerate(nodes):
        node_tokens = _estimate_node_tokens(node, index)

        exceeds_limits = (
            len(current_batch) >= MAX_NODES_PER_BATCH
            or current_tokens + node_tokens > MAX_TOKENS_PER_BATCH
        )

        if current_batch and exceeds_limits:
            batches.append(current_batch)
            current_batch = []
            current_tokens = PROMPT_OVERHEAD_TOKENS

        current_batch.append(node)
        current_tokens += node_tokens

    if current_batch:
        batches.append(current_batch)

    return batches

class GeminiSummarizer(BaseSummarizer):

    def __init__(self) -> None:
        self._client = genai.Client(
            api_key=os.environ["GEMINI_API_KEY"]
        )

    def _call_api(self, prompt: str) -> str:
        for attempt in range(1, MAX_RATE_LIMIT_RETRIES + 1):
            try:
                wait_for_gemini_rate_limit()

                response = self._client.models.generate_content(
                    model=GEMINI_SUMMARIZER_CONFIG["model_name"],
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=GEMINI_SUMMARIZER_CONFIG["temperature"],
                        response_mime_type="application/json",
                    ),
                )

                if response.text:
                    return response.text

                return ""

            except APIError as e:
                if not _is_retryable_api_error(e):
                    raise

                if attempt == MAX_RATE_LIMIT_RETRIES:
                    logger.error(
                        "Gemini summarizer failed too many times with retryable errors; giving up."
                    )
                    raise

                wait_seconds = RATE_LIMIT_WAIT * attempt

                logger.warning(
                    "Gemini summarizer request failed with status %s; waiting %ss before retry %s/%s...",
                    e.code,
                    wait_seconds,
                    attempt + 1,
                    MAX_RATE_LIMIT_RETRIES,
                )

                time.sleep(wait_seconds)

        raise RuntimeError(
            "Gemini summarizer failed after rate-limit retries."
        )

    async def summarize_batch(
        self,
        nodes: list[CodeNode]
    ) -> dict[str, str]:

        results: dict[str, str] = {}

        summarizable = [
            node
            for node in nodes
            if node.type in {
                CodeNodeType.FUNCTION,
                CodeNodeType.CLASS,
            }
            and node.raw_source
        ]

        batches = _make_batches(summarizable)
        total_batches = len(batches)

        # Debug logging
        print(f"\nTotal summarizable nodes: {len(summarizable)}")
        print(f"Total batches: {total_batches}")

        for i, batch in enumerate(batches, start=1):
            estimated_tokens = (
                PROMPT_OVERHEAD_TOKENS
                + sum(
                    _estimate_node_tokens(node, j)
                    for j, node in enumerate(batch)
                )
            )

            print(
                f"  Batch {i}: "
                f"{len(batch)} nodes, "
                f"~{estimated_tokens:,} tokens"
            )

        print()

        for i, batch in enumerate(batches, start=1):
            prepared_nodes = [
                _prepare_node(node)
                for node in batch
            ]

            prompt = _render_prompt(prepared_nodes)

            estimated_tokens = _estimate_tokens(prompt)

            logger.info(
                f"Batch {i}/{total_batches} - "
                f"{len(batch)} nodes, "
                f"~{estimated_tokens:,} tokens"
            )

            text = await asyncio.to_thread(
                self._call_api,
                prompt,
            )

            if not text:
                continue

            parsed = json.loads(text)

            for item in parsed:
                results[item["id"]] = item["summary"]

        return results