import os
import json
import time
import logging
from google import genai
from google.genai import types
from google.genai.errors import APIError
from app.schemas.node import CodeNode, CodeNodeType
from app.llm.summarizer.base import BaseSummarizer

logger = logging.getLogger(__name__)

# Limits
MAX_TOKENS_PER_BATCH = 50_000
MAX_NODES_PER_BATCH = 20
CHARS_PER_TOKEN = 4
RATE_LIMIT_WAIT = 65
MAX_RATE_LIMIT_RETRIES = 3

PROMPT_TEMPLATE = """<role>
You are a senior software engineer generating summaries for a semantic code search system.
</role>
<task>
For each code node, produce a single, precise sentence describing what the code DOES.
</task>
<rules>
- One sentence per node (strict)
- Use active voice
- Focus on behavior, not structure
- Include inputs, outputs, and side effects if present
- Do NOT say "This function", "This class", or similar filler
- Do NOT repeat the node name unless necessary
- Do NOT explain obvious syntax
- Avoid vague words like "handles", "manages", "processes" unless clarified
- Be specific and technical
</rules>
<output_format>
Return ONLY valid JSON in this exact structure:
[
  {{ "id": "<node_id>", "summary": "<one sentence>" }}
]
- Preserve the SAME ORDER as input
- Do not include any extra text, comments, or markdown
</output_format>
<context>
Each node contains:
- ID
- Name
- Type (function or class)
- Metadata (args, returns, inheritance)
- Source code
</context>
<example>
Input:
### NODE 0
ID: 123
Name: add_numbers
Type: FUNCTION
Meta: Args: {{"a": "int", "b": "int"}} | Returns: int
Code:
def add_numbers(a, b):
    return a + b

Output:
[
  {{ "id": "123", "summary": "Returns the sum of two integers." }}
]
</example>
<data>
{blocks}
</data>"""


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


class GeminiSummarizer(BaseSummarizer):

    def __init__(self) -> None:
        self._client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    def _call_api(self, prompt: str) -> str:
        for attempt in range(1, MAX_RATE_LIMIT_RETRIES + 1):
            try:
                response = self._client.models.generate_content(
                    model="gemini-2.5-flash-lite",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.1,
                        response_mime_type="application/json",
                    ),
                )
                if response.text:
                    return response.text
                return ""
            except APIError as e:
                if e.code != 429:
                    raise

                if attempt == MAX_RATE_LIMIT_RETRIES:
                    logger.error("Rate limit hit too many times; giving up.")
                    raise

                wait_seconds = RATE_LIMIT_WAIT * attempt
                logger.warning(
                    f"Rate limit hit; waiting {wait_seconds}s before retry "
                    f"{attempt + 1}/{MAX_RATE_LIMIT_RETRIES}..."
                )
                time.sleep(wait_seconds)

        raise RuntimeError("Gemini summarizer failed after rate-limit retries.")

    def summarize_batch(self, nodes: list[CodeNode]) -> dict[str, str]:
        results: dict[str, str] = {}

        summarizable = [
            n for n in nodes
            if n.type in {CodeNodeType.FUNCTION, CodeNodeType.CLASS}
            and n.raw_source
        ]

        batches = _make_batches(summarizable)
        total = len(batches)

        # debug
        print(f"\nTotal summarizable nodes: {len(summarizable)}")
        print(f"Total batches: {total}")
        for i, batch in enumerate(batches, start=1):
            est = PROMPT_OVERHEAD_TOKENS + sum(
                _estimate_tokens(_build_node_block(j, n)) for j, n in enumerate(batch)
            )
            print(f"  Batch {i}: {len(batch)} nodes, ~{est:,} tokens")
        print()

        for i, batch in enumerate(batches, start=1):
            batch_blocks = [_build_node_block(j, n) for j, n in enumerate(batch)]
            est_tokens = PROMPT_OVERHEAD_TOKENS + sum(
                _estimate_tokens(block) for block in batch_blocks
            )
            logger.info(
                f"Batch {i}/{total} - {len(batch)} nodes, ~{est_tokens:,} tokens"
            )

            blocks = "\n\n".join(batch_blocks)
            prompt = PROMPT_TEMPLATE.format(blocks=blocks)

            text = self._call_api(prompt)

            if text:
                parsed = json.loads(text)
                for item in parsed:
                    results[item["id"]] = item["summary"]

        return results