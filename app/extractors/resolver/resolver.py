from __future__ import annotations
from app.schemas.edge import CodeEdge, CodeEdgeType
from app.schemas.node import CodeNode, CodeNodeType


def resolve_edges(nodes: list[CodeNode], edges: list[CodeEdge]) -> tuple[int, int, list[CodeEdge]]:
    node_by_id: dict[str, CodeNode] = {}
    node_by_path: dict[str, list[CodeNode]] = {}
    node_by_qname: dict[str, list[CodeNode]] = {}
    node_by_name: dict[str, list[CodeNode]] = {}
    module_by_path: dict[str, CodeNode] = {}

    for node in nodes:
        if node.id in node_by_id:
            continue
        node_by_id[node.id] = node
        if node.path:
            node_by_path.setdefault(node.path, []).append(node)
            if node.type == CodeNodeType.MODULE:
                module_by_path[node.path] = node
        if node.qualified_name:
            node_by_qname.setdefault(node.qualified_name, []).append(node)
        if node.name:
            node_by_name.setdefault(node.name, []).append(node)

    # import_map: module_node_id -> [{"name": str, "module_ref": str}]
    # stores named imports and wildcard markers, no expansion at build time
    import_map: dict[str, list[dict[str, str]]] = {}
    for edge in edges:
        if edge.type != CodeEdgeType.IMPORTS or not edge.target_ref:
            continue
        bindings = (edge.attributes or {}).get("bindings", [])
        for b in bindings:
            if not isinstance(b, dict):
                continue
            name = b.get("alias") or b.get("name")
            if name:
                import_map.setdefault(edge.source_id, []).append({
                    "name": name,
                    "module_ref": edge.target_ref,
                })

    resolved = 0
    unresolved = 0

    for edge in edges:
        if edge.target_id is not None or not edge.target_ref or edge.type != CodeEdgeType.IMPORTS:
            continue
        target = _resolve_import(edge, module_by_path)
        if target is not None:
            edge.target_id = target.id
            resolved += 1
        else:
            unresolved += 1

    for edge in edges:
        if edge.target_id is not None or not edge.target_ref or edge.type != CodeEdgeType.INHERITS:
            continue
        target = _resolve_inherits(edge, import_map, node_by_id, node_by_qname, node_by_name, module_by_path)
        if target is not None:
            edge.target_id = target.id
            resolved += 1
        else:
            unresolved += 1

    for edge in edges:
        if edge.target_id is not None or not edge.target_ref or edge.type != CodeEdgeType.CALLS:
            continue
        target = _resolve_call(edge, import_map, node_by_id, node_by_qname, node_by_name, module_by_path)
        if target is not None:
            edge.target_id = target.id
            resolved += 1
        else:
            unresolved += 1

    return resolved, unresolved, edges


def _resolve_import(
    edge: CodeEdge,
    module_by_path: dict[str, CodeNode],
) -> CodeNode | None:
    if not edge.target_ref:
        return None
    path = edge.target_ref.replace(".", "/") + ".py"
    return module_by_path.get(path)


def _resolve_call(
    edge: CodeEdge,
    import_map: dict[str, list[dict[str, str]]],
    node_by_id: dict[str, CodeNode],
    node_by_qname: dict[str, list[CodeNode]],
    node_by_name: dict[str, list[CodeNode]],
    module_by_path: dict[str, CodeNode],
) -> CodeNode | None:
    if not edge.target_ref:
        return None

    is_self_or_cls = False

    # strip self./cls.
    parts = edge.target_ref.split(".")
    if parts[0] in {"self", "cls"}:
        is_self_or_cls = True
        parts = parts[1:]
    target = ".".join(parts)
    if not target:
        return None

    # get source node and its parent module
    # works for both top-level functions and methods inside classes
    # because all nodes share the same path regardless of nesting
    source_node = node_by_id.get(edge.source_id)
    if not source_node or not source_node.path:
        return None
    source_module = module_by_path.get(source_node.path)
    if not source_module or not source_module.qualified_name:
        return None

    # 1. local — search by qualified name within this module
    if (
        is_self_or_cls
        and source_node.qualified_name
        and source_node.qualified_name.startswith(f"{source_module.qualified_name}.")
    ):
        relative_qname = source_node.qualified_name[len(source_module.qualified_name) + 1:]
        relative_parts = relative_qname.split(".")
        if len(relative_parts) >= 2:
            class_qname = (
                f"{source_module.qualified_name}.{'.'.join(relative_parts[:-1])}"
            )
            local = node_by_qname.get(f"{class_qname}.{target}")
            if local:
                return local[0]

    local = node_by_qname.get(f"{source_module.qualified_name}.{target}")
    if local:
        return local[0]

    # 2. named import — check import_map for this module
    imports = import_map.get(source_module.id, [])
    for entry in imports:
        if entry["name"] == target and entry["name"] != "*":
            qualified = f"{entry['module_ref']}.{target}"
            candidates = node_by_qname.get(qualified)
            if candidates:
                return candidates[0]

    # 3. wildcard import — search by name in any * imported module
    for entry in imports:
        if entry["name"] == "*":
            file_path = entry["module_ref"].replace(".", "/") + ".py"
            module_node = module_by_path.get(file_path)
            if not module_node or not module_node.qualified_name:
                continue
            qualified = f"{module_node.qualified_name}.{target}"
            candidates = node_by_qname.get(qualified)
            if candidates:
                return candidates[0]

    return None


def _resolve_inherits(
    edge: CodeEdge,
    import_map: dict[str, list[dict[str, str]]],
    node_by_id: dict[str, CodeNode],
    node_by_qname: dict[str, list[CodeNode]],
    node_by_name: dict[str, list[CodeNode]],
    module_by_path: dict[str, CodeNode],
) -> CodeNode | None:
    if not edge.target_ref:
        return None

    target = edge.target_ref
    source_node = node_by_id.get(edge.source_id)
    source_module = module_by_path.get(str(source_node.path)) if source_node else None

    # 1. local class in same module
    if source_module and source_module.qualified_name:
        local = node_by_qname.get(f"{source_module.qualified_name}.{target}")
        if local and local[0].type == CodeNodeType.CLASS:
            return local[0]

    # 2. named import
    if source_module:
        for entry in import_map.get(source_module.id, []):
            if entry["name"] == target:
                qualified = f"{entry['module_ref']}.{target}"
                candidates = node_by_qname.get(qualified)
                if candidates and candidates[0].type == CodeNodeType.CLASS:
                    return candidates[0]

    # 3. wildcard import
    if source_module:
        for entry in import_map.get(source_module.id, []):
            if entry["name"] == "*":
                file_path = entry["module_ref"].replace(".", "/") + ".py"
                module_node = module_by_path.get(file_path)
                if not module_node or not module_node.qualified_name:
                    continue
                qualified = f"{module_node.qualified_name}.{target}"
                candidates = node_by_qname.get(qualified)
                if candidates and candidates[0].type == CodeNodeType.CLASS:
                    return candidates[0]

    # 4. fallback — search by name across codebase
    candidates = [n for n in node_by_name.get(target, []) if n.type == CodeNodeType.CLASS]
    return candidates[0] if candidates else None


__all__ = ["resolve_edges"]
