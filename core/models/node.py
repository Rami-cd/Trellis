from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CodeNodeType(str, Enum):
    """Language-agnostic categories for code entities."""

    FUNCTION = "function"
    CLASS = "class"
    FILE = "file"
    MODULE = "module"
    VARIABLE = "variable"


@dataclass(slots=True)
class CodeNode:
    """
    Represents a single entity in the code knowledge graph.

    The model stays intentionally small so the core layer is reusable across
    parsers, storage backends, and explanation pipelines.
    """

    id: str
    type: CodeNodeType
    name: str
    language: str | None = None
    path: str | None = None
    qualified_name: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    raw_source: str | None = None

    def __post_init__(self) -> None:
        if not self.id or not self.id.strip():
            raise ValueError("CodeNode.id must be a non-empty string.")
        if not self.name or not self.name.strip():
            raise ValueError("CodeNode.name must be a non-empty string.")
        if self.start_line is not None and self.start_line < 1:
            raise ValueError("CodeNode.start_line must be >= 1 when provided.")
        if self.end_line is not None and self.end_line < 1:
            raise ValueError("CodeNode.end_line must be >= 1 when provided.")
        if (
            self.start_line is not None
            and self.end_line is not None
            and self.end_line < self.start_line
        ):
            raise ValueError("CodeNode.end_line must be >= start_line.")

        self.id = self.id.strip()
        self.name = self.name.strip()
        self.language = self.language.strip() if self.language else None
        self.path = self.path.strip() if self.path else None
        self.qualified_name = (
            self.qualified_name.strip() if self.qualified_name else None
        )
        self.attributes = dict(self.attributes)


__all__ = ["CodeNode", "CodeNodeType"]
