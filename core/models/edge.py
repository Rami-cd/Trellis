from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

class CodeEdgeType(str, Enum): 
    CALLS = "calls"
    IMPORTS = "imports"
    DEFINES = "defines"
    INHERITS = "inherits"

@dataclass(slots=True)
class CodeEdge:
    id: str
    source_id: str
    target_id: str | None
    target_ref: str | None
    type: CodeEdgeType
    attributes: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id or not self.id.strip():
            raise ValueError("CodeEdge.id must be a non-empty string.")
        if not self.source_id or not self.source_id.strip():
            raise ValueError("CodeEdge.source_id must be a non-empty string.")
        if self.target_id is not None:
            self.target_id = self.target_id.strip()
            if not self.target_id:
                raise ValueError("CodeEdge.target_id cannot be empty if provided.")
        if self.target_id is None and not self.target_ref:
            raise ValueError("Either target_id or target_ref must be provided.")

        self.id = self.id.strip()
        self.source_id = self.source_id.strip()
        self.attributes = dict(self.attributes)

__all__ = ["CodeEdge", "CodeEdgeType"]