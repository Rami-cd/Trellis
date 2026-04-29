from __future__ import annotations
from abc import ABC, abstractmethod
from core.models.node import CodeNode
from core.models.edge import CodeEdge
from tree_sitter import Tree

class BaseExtractor(ABC):

    @property
    @abstractmethod
    def language(self) -> str:
        ...

    @abstractmethod
    def extract(self, tree: Tree, source: bytes, file_path: str) -> tuple[list[CodeNode], list[CodeEdge]]:
        ...

__all__ = ["BaseExtractor"]