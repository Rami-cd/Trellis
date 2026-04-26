from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any

class BaseParser(ABC):
    @property
    @abstractmethod
    def language(self) -> str:
        pass
    
    @abstractmethod
    def parse(self, source: str, file_path: str) -> Any:
        pass

__all__ = ["BaseParser"]