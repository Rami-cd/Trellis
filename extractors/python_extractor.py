from __future__ import annotations

from pathlib import PurePath
from typing import Any, Iterator

from core.models.edge import CodeEdge, CodeEdgeType
from core.models.graph import ProjectGraph
from core.models.node import CodeNode, CodeNodeType
from extractors.base_extractor import BaseExtractor


class PythonExtractor(BaseExtractor):
    """
    Extract a language-agnostic project graph from a Python tree-sitter AST.

    Grammar notes used by this extractor:
    - functions: ``function_definition`` with an immediate ``identifier`` child
    - classes: ``class_definition`` with an immediate ``identifier`` child
    - imports: ``import_statement`` and ``import_from_statement``
    - direct function calls: ``call`` with an immediate ``identifier`` child
    """

    def __init__(self) -> None:
        self._current_file_path: str | None = None

    @property
    def language(self) -> str:
        """Return the language handled by this extractor."""

        return "python"

    def extract(self, tree: Any, source: str, file_path: str) -> ProjectGraph:
        """Extract module, class, function, defines, and calls relationships."""

        self._current_file_path = file_path
        source_bytes = source.encode("utf-8")
        graph = ProjectGraph()
        root = tree.root_node

        module_id = f"{file_path}::module"
        graph.add_node(
            CodeNode(
                id=module_id,
                type=CodeNodeType.MODULE,
                name=PurePath(file_path).stem,
                language=self.language,
                path=file_path,
                qualified_name=module_id,
                start_line=1,
                end_line=root.end_point.row + 1,
            )
        )

        for node in self._walk(root):
            if node.type == "function_definition":
                function_node = self._build_definition_node(
                    node=node,
                    file_path=file_path,
                    source_bytes=source_bytes,
                    node_type=CodeNodeType.FUNCTION,
                )
                if function_node is not None:
                    graph.add_node(function_node)
            elif node.type == "class_definition":
                class_node = self._build_definition_node(
                    node=node,
                    file_path=file_path,
                    source_bytes=source_bytes,
                    node_type=CodeNodeType.CLASS,
                )
                if class_node is not None:
                    graph.add_node(class_node)

        for child in root.children:
            if child.type not in {"function_definition", "class_definition"}:
                continue

            child_name = self._get_identifier(child)
            if child_name is None:
                continue

            child_id = f"{file_path}::{child_name}"
            edge_id = f"defines::{module_id}::{child_id}"
            if not graph.has_edge(edge_id) and graph.has_node(child_id):
                graph.add_edge(
                    CodeEdge(
                        id=edge_id,
                        source_id=module_id,
                        target_id=child_id,
                        type=CodeEdgeType.DEFINES,
                    )
                )

        for node in self._walk(root):
            if node.type != "call":
                continue

            source_id = self._find_enclosing_function(node)
            called_name = self._get_identifier(node)
            if source_id is None or called_name is None:
                continue

            target_id = f"{file_path}::{called_name}"
            edge_id = f"call::{source_id}::{target_id}"
            if (
                graph.has_node(source_id)
                and graph.has_node(target_id)
                and not graph.has_edge(edge_id)
            ):
                graph.add_edge(
                    CodeEdge(
                        id=edge_id,
                        source_id=source_id,
                        target_id=target_id,
                        type=CodeEdgeType.CALLS,
                    )
                )

        return graph

    def _build_definition_node(
        self,
        *,
        node: Any,
        file_path: str,
        source_bytes: bytes,
        node_type: CodeNodeType,
    ) -> CodeNode | None:
        name = self._get_identifier(node)
        if name is None:
            return None

        node_id = f"{file_path}::{name}"
        return CodeNode(
            id=node_id,
            type=node_type,
            name=name,
            language=self.language,
            path=file_path,
            qualified_name=node_id,
            start_line=node.start_point.row + 1,
            end_line=node.end_point.row + 1,
            raw_source=self._get_source(node, source_bytes),
        )

    def _get_source(self, node: Any, source_bytes: bytes) -> str:
        """Return the exact source slice represented by a tree-sitter node."""

        return source_bytes[node.start_byte : node.end_byte].decode("utf-8")

    def _find_enclosing_function(self, node: Any) -> str | None:
        """Walk upward through parents and return the enclosing function id."""

        current = node.parent
        while current is not None:
            if current.type == "function_definition":
                function_name = self._get_identifier(current)
                if function_name is None or self._current_file_path is None:
                    return None
                return f"{self._current_file_path}::{function_name}"
            current = current.parent
        return None

    def _get_identifier(self, node: Any) -> str | None:
        """Return the first immediate identifier child for a node, if any."""

        for child in node.children:
            if child.type == "identifier":
                return child.text.decode("utf-8")
        return None

    def _walk(self, node: Any) -> Iterator[Any]:
        """Yield a node and all descendants using ``children`` traversal only."""

        yield node
        for child in node.children:
            yield from self._walk(child)


__all__ = ["PythonExtractor"]