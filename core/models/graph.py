from __future__ import annotations
 
from dataclasses import dataclass, field
from typing import Any, Iterable, Literal

from core.models.edge import CodeEdge, CodeEdgeType
from core.models.node import CodeNode, CodeNodeType


Direction = Literal["incoming", "outgoing", "both"]


@dataclass(slots=True)
class ProjectGraph:
    """
    Pure in-memory abstraction for a code knowledge graph.

    The graph owns node and edge collections plus lightweight adjacency indexes
    to keep queries efficient without depending on any graph library.
    """

    nodes: dict[str, CodeNode] = field(default_factory=dict)
    edges: dict[str, CodeEdge] = field(default_factory=dict)
    _outgoing_index: dict[str, dict[str, None]] = field(
        default_factory=dict,
        init=False,
        repr=False,
    )
    _incoming_index: dict[str, dict[str, None]] = field(
        default_factory=dict,
        init=False,
        repr=False,
    )

    def add_node(self, node: CodeNode, *, replace: bool = False) -> CodeNode:
        if node.id in self.nodes and not replace:
            raise ValueError(f"Node '{node.id}' already exists.")

        self.nodes[node.id] = node
        self._outgoing_index.setdefault(node.id, {})
        self._incoming_index.setdefault(node.id, {})
        return node

    def add_nodes(
        self,
        nodes: Iterable[CodeNode],
        *,
        replace: bool = False,
    ) -> list[CodeNode]:
        return [self.add_node(node, replace=replace) for node in nodes]

    def get_node(self, node_id: str) -> CodeNode | None:
        return self.nodes.get(node_id)

    def has_node(self, node_id: str) -> bool:
        return node_id in self.nodes

    def remove_node(self, node_id: str) -> CodeNode | None:
        node = self.nodes.get(node_id)
        if node is None:
            return None

        connected_edge_ids = list(self._incoming_index.get(node_id, {}).keys())
        connected_edge_ids.extend(self._outgoing_index.get(node_id, {}).keys())

        for edge_id in dict.fromkeys(connected_edge_ids):
            self.remove_edge(edge_id)

        self._incoming_index.pop(node_id, None)
        self._outgoing_index.pop(node_id, None)
        return self.nodes.pop(node_id)

    def add_edge(self, edge: CodeEdge, *, replace: bool = False) -> CodeEdge:
        if edge.id in self.edges and not replace:
            raise ValueError(f"Edge '{edge.id}' already exists.")
        if edge.source_id not in self.nodes:
            raise ValueError(f"Source node '{edge.source_id}' does not exist.")
        if edge.target_id not in self.nodes:
            raise ValueError(f"Target node '{edge.target_id}' does not exist.")

        if replace and edge.id in self.edges:
            self.remove_edge(edge.id)

        self.edges[edge.id] = edge
        self._outgoing_index.setdefault(edge.source_id, {})[edge.id] = None
        self._incoming_index.setdefault(edge.target_id, {})[edge.id] = None
        return edge

    def add_edges(
        self,
        edges: Iterable[CodeEdge],
        *,
        replace: bool = False,
    ) -> list[CodeEdge]:
        return [self.add_edge(edge, replace=replace) for edge in edges]

    def get_edge(self, edge_id: str) -> CodeEdge | None:
        return self.edges.get(edge_id)

    def has_edge(self, edge_id: str) -> bool:
        return edge_id in self.edges

    def remove_edge(self, edge_id: str) -> CodeEdge | None:
        edge = self.edges.pop(edge_id, None)
        if edge is None:
            return None

        self._outgoing_index.get(edge.source_id, {}).pop(edge_id, None)
        self._incoming_index.get(edge.target_id, {}).pop(edge_id, None)
        return edge

    def find_nodes(
        self,
        *,
        node_type: CodeNodeType | None = None,
        language: str | None = None,
        path: str | None = None,
        name: str | None = None,
        qualified_name: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> list[CodeNode]:
        matches: list[CodeNode] = []

        for node in self.nodes.values():
            if node_type is not None and node.type != node_type:
                continue
            if language is not None and node.language != language:
                continue
            if path is not None and node.path != path:
                continue
            if name is not None and node.name != name:
                continue
            if qualified_name is not None and node.qualified_name != qualified_name:
                continue
            if attributes is not None and not self._matches_attributes(
                node.attributes,
                attributes,
            ):
                continue
            matches.append(node)

        return matches

    def find_edges(
        self,
        *,
        edge_type: CodeEdgeType | None = None,
        source_id: str | None = None,
        target_id: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> list[CodeEdge]:
        matches: list[CodeEdge] = []

        for edge in self.edges.values():
            if edge_type is not None and edge.type != edge_type:
                continue
            if source_id is not None and edge.source_id != source_id:
                continue
            if target_id is not None and edge.target_id != target_id:
                continue
            if attributes is not None and not self._matches_attributes(
                edge.attributes,
                attributes,
            ):
                continue
            matches.append(edge)

        return matches

    def outgoing_edges(
        self,
        node_id: str,
        *,
        edge_type: CodeEdgeType | None = None,
    ) -> list[CodeEdge]:
        return self._indexed_edges(self._outgoing_index.get(node_id, {}), edge_type)

    def incoming_edges(
        self,
        node_id: str,
        *,
        edge_type: CodeEdgeType | None = None,
    ) -> list[CodeEdge]:
        return self._indexed_edges(self._incoming_index.get(node_id, {}), edge_type)

    def neighbors(
        self,
        node_id: str,
        *,
        direction: Direction = "outgoing",
        edge_type: CodeEdgeType | None = None,
    ) -> list[CodeNode]:
        if direction not in {"incoming", "outgoing", "both"}:
            raise ValueError("direction must be 'incoming', 'outgoing', or 'both'.")

        neighbor_ids: dict[str, None] = {}

        if direction in {"outgoing", "both"}:
            for edge in self.outgoing_edges(node_id, edge_type=edge_type):
                neighbor_ids[edge.target_id] = None

        if direction in {"incoming", "both"}:
            for edge in self.incoming_edges(node_id, edge_type=edge_type):
                neighbor_ids[edge.source_id] = None

        return [self.nodes[neighbor_id] for neighbor_id in neighbor_ids]

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return len(self.edges)

    def _indexed_edges(
        self,
        index: dict[str, None],
        edge_type: CodeEdgeType | None,
    ) -> list[CodeEdge]:
        matches: list[CodeEdge] = []

        for edge_id in index:
            edge = self.edges[edge_id]
            if edge_type is None or edge.type == edge_type:
                matches.append(edge)

        return matches

    @staticmethod
    def _matches_attributes(
        source: dict[str, Any],
        required: dict[str, Any],
    ) -> bool:
        for key, value in required.items():
            if source.get(key) != value:
                return False
        return True


__all__ = ["ProjectGraph"]
