from __future__ import annotations
from typing import Any
from tree_sitter import Language, Parser
import tree_sitter_python as tspython
from core.exceptions import ParseError
from parsers.base_parser import BaseParser

class PythonParser(BaseParser):

    def __init__(self) -> None:
        PY_LANGUAGE = Language(tspython.language())
        self._parser = Parser(PY_LANGUAGE)

    @property
    def language(self) -> str:
        return "python"

    def parse(self, source: str, file_path: str) -> Any:
        if not source or not source.strip():
            raise ValueError("source must not be empty.")

        tree = self._parser.parse(source.encode("utf-8"))

        if tree.root_node.has_error:
            raise ParseError(f"Failed to parse Python source in '{file_path}'.")
        return tree

__all__ = ["PythonParser"]