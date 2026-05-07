from __future__ import annotations

import json
import logging
import time
import requests

from app.schemas.node import CodeNode, CodeNodeType
from app.llm.summarizer.base import BaseSummarizer

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = "http://localhost:11434"
MODEL_NAME = "qwen2.5-coder:7b-instruct"

# Reduced batch size — small models lose coherence fast with many items
MAX_TOKENS_PER_BATCH = 4_000
MAX_SINGLE_NODE_TOKENS = 3_500
MAX_NODES_PER_BATCH = 3
CHARS_PER_TOKEN = 3  # Code is denser than prose; 3 is more accurate than 4

MAX_RETRIES = 3
RETRY_WAIT = 5

SYSTEM_PROMPT = (
    "You are a senior software engineer. "
    "Return concise, technical summaries that describe what each code node does."
)

# Root must be an object — Ollama's grammar enforcement doesn't handle array roots reliably
OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "summaries": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "summary": {"type": "string"},
                },
                "required": ["id", "summary"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["summaries"],
    "additionalProperties": False,
}

# Simplified prompt — small models follow 2-3 rules well, not 10
PROMPT_TEMPLATE = """For each code node below, write one technical sentence describing what it does.
Focus on inputs, outputs, and side effects. Be specific. Active voice.

{blocks}

Return JSON matching this shape exactly: {{"summaries": [{{"id": "...", "summary": "..."}}]}}"""

# Single-node prompt is even simpler — used for fallback recovery
SINGLE_NODE_PROMPT_TEMPLATE = """Describe what this code does in one technical sentence.
Focus on inputs, outputs, and side effects.

{block}

Return JSON: {{"summaries": [{{"id": "...", "summary": "..."}}]}}"""


def _estimate_tokens(text: str) -> int:
    return (len(text) + CHARS_PER_TOKEN - 1) // CHARS_PER_TOKEN


def _build_node_block(index: int, node: CodeNode) -> str:
    if node.type == CodeNodeType.FUNCTION:
        args = dict(node.attributes.get("args", {}))
        returns = node.attributes.get("returns", "None")
        meta = f"Args: {args} | Returns: {returns}"
    elif node.type == CodeNodeType.CLASS:
        bases = list(node.attributes.get("bases", []))
        meta = f"Inherits from: {bases if bases else 'nothing'}"
    else:
        meta = ""

    return f"""### NODE {index}
ID: {node.id}
Name: {node.qualified_name}
Type: {node.type.value}
Meta: {meta}
Code:
{node.raw_source}"""


PROMPT_OVERHEAD_TOKENS = _estimate_tokens(PROMPT_TEMPLATE.format(blocks=""))


def _make_batches(nodes: list[CodeNode]) -> list[list[CodeNode]]:
    batches: list[list[CodeNode]] = []
    current: list[CodeNode] = []
    current_tokens = PROMPT_OVERHEAD_TOKENS

    for index, node in enumerate(nodes):
        node_tokens = _estimate_tokens(_build_node_block(index, node))

        if node_tokens > MAX_SINGLE_NODE_TOKENS:
            logger.warning(
                "Skipping node '%s' — too large (%d tokens)",
                node.qualified_name,
                node_tokens,
            )
            continue

        if current and (
            len(current) >= MAX_NODES_PER_BATCH
            or current_tokens + node_tokens > MAX_TOKENS_PER_BATCH
        ):
            batches.append(current)
            current = []
            current_tokens = PROMPT_OVERHEAD_TOKENS

        current.append(node)
        current_tokens += node_tokens

    if current:
        batches.append(current)

    return batches


def _parse_response(text: str) -> list[dict] | None:
    """
    Parse the model's JSON response. Since we enforce a root object schema via Ollama,
    we expect {"summaries": [...]} — anything else is a model failure we try to recover from.
    """
    text = text.strip()

    # Strip markdown fences if the model ignored the schema constraint
    if "```" in text:
        parts = text.split("```")
        if len(parts) >= 2:
            text = parts[1].strip()
            if text.startswith("json"):
                text = text[4:].strip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None

    # Expected path: {"summaries": [...]}
    if isinstance(parsed, dict):
        if "summaries" in parsed and isinstance(parsed["summaries"], list):
            return parsed["summaries"]

        # Fallback: model returned a single item {"id": ..., "summary": ...}
        if "id" in parsed and "summary" in parsed:
            return [parsed]

        # Fallback: model wrapped items under some other key
        for v in parsed.values():
            if isinstance(v, list):
                return v

        return None

    # Fallback: model returned a bare array despite the schema
    if isinstance(parsed, list):
        return parsed

    return None


class QwenSummarizer(BaseSummarizer):
    def __init__(self) -> None:
        self.base_url = OLLAMA_BASE_URL
        self.model = MODEL_NAME
        self._session = requests.Session()

    def _call_api(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "format": OUTPUT_SCHEMA,
            "options": {
                "temperature": 0,
            },
        }

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = self._session.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                    timeout=180,
                )
                response.raise_for_status()
                return response.json()["message"]["content"].strip()

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

    def _summarize_one(self, node: CodeNode) -> str | None:
        """Fallback: summarize a single node with a simpler, focused prompt."""
        block = _build_node_block(0, node)
        prompt = SINGLE_NODE_PROMPT_TEMPLATE.format(block=block)
        text = self._call_api(prompt)
        if not text:
            return None

        parsed = _parse_response(text)
        if not parsed:
            return None

        for item in parsed:
            if item.get("id") == node.id and isinstance(item.get("summary"), str):
                return item["summary"].strip()

        # If ID matching fails, just take the first summary — single node, only one result
        if parsed and isinstance(parsed[0].get("summary"), str):
            logger.debug(
                "Node '%s': ID mismatch in single-node response, using first result anyway",
                node.qualified_name,
            )
            return parsed[0]["summary"].strip()

        return None

    def summarize_batch(self, nodes: list[CodeNode]) -> dict[str, str]:
        results: dict[str, str] = {}

        summarizable = [
            n for n in nodes
            if n.type in {CodeNodeType.FUNCTION, CodeNodeType.CLASS}
            and n.raw_source
        ]

        batches = _make_batches(summarizable)
        total = len(batches)

        logger.info("Total summarizable nodes: %d", len(summarizable))
        logger.info("Total batches: %d", total)

        for i, batch in enumerate(batches, start=1):
            batch_blocks = [_build_node_block(j, n) for j, n in enumerate(batch)]
            est_tokens = PROMPT_OVERHEAD_TOKENS + sum(
                _estimate_tokens(block) for block in batch_blocks
            )
            logger.info(
                "Batch %d/%d — %d nodes, ~%s tokens",
                i, total, len(batch), f"{est_tokens:,}",
            )

            blocks = "\n\n".join(batch_blocks)
            prompt = PROMPT_TEMPLATE.format(blocks=blocks)
            text = self._call_api(prompt)

            if not text:
                logger.warning("Batch %d: empty response, falling back to one-by-one", i)
                self._recover_batch(i, batch, results)
                continue

            parsed = _parse_response(text)

            if parsed is None:
                logger.warning("Batch %d: could not parse response | raw: %.300s", i, text)
                self._recover_batch(i, batch, results)
                continue

            batch_ids = {node.id for node in batch}
            returned_ids = set()

            if len(parsed) < len(batch):
                logger.warning(
                    "Batch %d: model returned %d items for %d nodes",
                    i, len(parsed), len(batch),
                )

            for item in parsed:
                item_id = item.get("id")
                summary = item.get("summary")
                if isinstance(item_id, str) and isinstance(summary, str):
                    results[item_id] = summary.strip()
                    returned_ids.add(item_id)
                else:
                    logger.warning("Batch %d: malformed item: %s", i, item)

            missing_ids = batch_ids - returned_ids
            if missing_ids:
                logger.warning(
                    "Batch %d: missing %d summaries, retrying individually",
                    i, len(missing_ids),
                )
                id_to_node = {node.id: node for node in batch}
                for missing_id in missing_ids:
                    node = id_to_node[missing_id]
                    summary = self._summarize_one(node)
                    if summary:
                        results[node.id] = summary
                    else:
                        logger.warning(
                            "Batch %d: failed to recover summary for '%s' (%s)",
                            i, node.id, node.qualified_name,
                        )

        return results

    def _recover_batch(self, batch_index: int, batch: list[CodeNode], results: dict[str, str]) -> None:
        """Retry every node in a failed batch individually."""
        for node in batch:
            summary = self._summarize_one(node)
            if summary:
                results[node.id] = summary
            else:
                logger.warning(
                    "Batch %d: failed to recover summary for '%s' (%s)",
                    batch_index, node.id, node.qualified_name,
                )