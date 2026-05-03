from __future__ import annotations

MAX_PROMPT_CHARS = 20_000
PRIMARY_SOURCE_LINE_LIMIT = 15


def _truncate_to_lines(text: str, max_lines: int) -> str:
    if not text:
        return ""
    return "\n".join(text.splitlines()[:max_lines])


def _render_node_block(node: dict) -> str:
    qualified_name = node.get("qualified_name") or "N/A"
    node_type = node.get("type") or "N/A"
    summary = node.get("summary") or "N/A"
    raw_source = (node.get("raw_source") or "").rstrip()
    return (
        f"> {qualified_name} ({node_type})\n"
        f"Summary: {summary}\n"
        f"{raw_source}\n"
        "---"
    )


def _render_relationships(edges: list[dict], node_index: dict[str, dict]) -> str:
    lines: list[str] = []

    for edge in edges:
        source_node = node_index.get(edge.get("source_id", ""))
        if not source_node or source_node.get("type") == "module":
            continue

        target_id = edge.get("target_id")
        target_node = node_index.get(target_id) if target_id else None
        if target_node and target_node.get("type") == "module":
            continue

        source_qualified_name = source_node.get("qualified_name") or edge.get("source_id") or "N/A"
        edge_type = edge.get("type") or "N/A"
        target_ref = edge.get("target_ref") or target_id or "N/A"
        lines.append(f"{source_qualified_name} --[{edge_type}]--> {target_ref}")

    return "\n".join(lines)


def _render_prompt(
    query: str,
    seed_nodes: list[dict],
    related_nodes: list[dict],
    edges: list[dict],
    node_index: dict[str, dict],
) -> str:
    primary_blocks = [_render_node_block(node) for node in seed_nodes]
    related_blocks = [_render_node_block(node) for node in related_nodes]
    relationships = _render_relationships(edges, node_index)

    parts = [
        "=== CODE CONTEXT ===",
        "",
        "[PRIMARY]",
        *primary_blocks,
        "",
        "[RELATED]",
        *related_blocks,
        "",
        "[RELATIONSHIPS]",
        relationships,
        "",
        "=== QUESTION ===",
        query,
    ]
    return "\n".join(parts)


def build_explanation_prompt(
    query: str,
    seed_nodes: list[dict],
    related_nodes: list[dict],
    edges: list[dict],
    node_index: dict[str, dict],
) -> str:
    filtered_seed_nodes = [node for node in seed_nodes if node.get("type") != "module"]
    filtered_related_nodes = [node for node in related_nodes if node.get("type") != "module"]

    prompt = _render_prompt(
        query=query,
        seed_nodes=filtered_seed_nodes,
        related_nodes=filtered_related_nodes,
        edges=edges,
        node_index=node_index,
    )
    if len(prompt) <= MAX_PROMPT_CHARS:
        return prompt

    # Reduce lower-priority context first before trimming the primary code blocks.
    related_without_source = [{**node, "raw_source": ""} for node in filtered_related_nodes]
    prompt = _render_prompt(
        query=query,
        seed_nodes=filtered_seed_nodes,
        related_nodes=related_without_source,
        edges=edges,
        node_index=node_index,
    )
    if len(prompt) <= MAX_PROMPT_CHARS:
        return prompt

    truncated_primary = [
        {**node, "raw_source": _truncate_to_lines(node.get("raw_source") or "", PRIMARY_SOURCE_LINE_LIMIT)}
        for node in filtered_seed_nodes
    ]
    return _render_prompt(
        query=query,
        seed_nodes=truncated_primary,
        related_nodes=related_without_source,
        edges=edges,
        node_index=node_index,
    )