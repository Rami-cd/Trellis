from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any
from core.models.graph import ProjectGraph

class BaseExtractor(ABC):
    """Abstract interface for language-specific code graph extractors.

    Concrete extractors consume a parser-produced syntax tree together with the
    original source text and file path, then return a populated ``ProjectGraph``.
    """

    @property
    @abstractmethod
    def language(self) -> str:
        """Return the language name handled by this extractor."""

    @abstractmethod
    def extract(self, tree: Any, source: str, file_path: str) -> ProjectGraph:
        """Extract graph data from a syntax tree and source file."""

__all__ = ["BaseExtractor"]