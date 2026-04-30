from __future__ import annotations
import logging
from tree_sitter import Language, Parser, Tree
import tree_sitter_python as tspython
from app.parsers.base_parser import BaseParser

logger = logging.getLogger(__name__)

class PythonParser(BaseParser):

    _PY_LANGUAGE = Language(tspython.language())

    @property
    def language(self) -> str:
        return "python"

    @property
    def supported_extensions(self) -> frozenset[str]:
        return frozenset({".py", ".pyw"})

    def parse(self, source: str, file_path: str) -> Tree | None:
        if not source or not source.strip():
            logger.debug("Skipping empty file: %s", file_path)
            return None

        try:
            encoded = source.encode("utf-8", errors="replace")
        except Exception as exc:
            logger.warning("Encoding failed for '%s': %s", file_path, exc)
            return None

        # New Parser per call — tree-sitter Parser is not thread-safe.
        parser = Parser(self._PY_LANGUAGE)
        tree = parser.parse(encoded)

        if tree.root_node.has_error:
            logger.warning("Partial syntax errors in '%s' — extracting valid nodes only.", file_path)

        return tree

__all__ = ["PythonParser"]