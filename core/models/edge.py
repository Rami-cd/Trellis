from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CodeEdgeType(str, Enum): 
    """Supported relationships between code entities."""

    CALLS = "calls"
    IMPORTS = "imports"
    DEFINES = "defines"
    INHERITS = "inherits"


@dataclass(slots=True)
class CodeEdge:
    """
    Represents a directed relationship in the code knowledge graph.

    Edges link node identifiers instead of concrete objects so the model stays
    storage-friendly and easy to serialize.
    """

    id: str
    source_id: str
    target_id: str
    type: CodeEdgeType
    attributes: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id or not self.id.strip():
            raise ValueError("CodeEdge.id must be a non-empty string.")
        if not self.source_id or not self.source_id.strip():
            raise ValueError("CodeEdge.source_id must be a non-empty string.")
        if not self.target_id or not self.target_id.strip():
            raise ValueError("CodeEdge.target_id must be a non-empty string.")

        self.id = self.id.strip()
        self.source_id = self.source_id.strip()
        self.target_id = self.target_id.strip()
        self.attributes = dict(self.attributes)


__all__ = ["CodeEdge", "CodeEdgeType"]
