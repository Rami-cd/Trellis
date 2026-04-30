from __future__ import annotations
from abc import ABC, abstractmethod
from tree_sitter import Tree

class BaseParser(ABC):

    @property
    @abstractmethod
    def language(self) -> str:
        ...

    @property
    @abstractmethod
    def supported_extensions(self) -> frozenset[str]:
        ...

    @abstractmethod
    def parse(self, source: str, file_path: str) -> Tree | None:
        ...

    def can_parse(self, file_path: str) -> bool:
        from pathlib import Path
        return Path(file_path).suffix.lower() in self.supported_extensions

__all__ = ["BaseParser"]