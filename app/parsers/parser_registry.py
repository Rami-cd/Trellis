from __future__ import annotations
from pathlib import Path
from typing import Iterable
from app.parsers.base_parser import BaseParser

class ParserRegistry:

    def __init__(self, parsers: Iterable[BaseParser] | None = None) -> None:
        self._parsers_by_language: dict[str, BaseParser] = {}
        self._parsers_by_extension: dict[str, BaseParser] = {}

        if parsers is not None:
            for parser in parsers:
                self.register(parser)

    def register(self, parser: BaseParser) -> None:
        language = self._normalize_language(parser.language)

        if language in self._parsers_by_language:
            raise ValueError(f"Parser already registered for language '{language}'")

        for extension in parser.supported_extensions:
            normalized_extension = self._normalize_extension(extension)
            existing_parser = self._parsers_by_extension.get(normalized_extension)
            if existing_parser is not None:
                raise ValueError(
                    "Parser already registered for extension"
                    f"'{normalized_extension}' via language '{existing_parser.language}'"
                )

        self._parsers_by_language[language] = parser

        for extension in parser.supported_extensions:
            self._parsers_by_extension[self._normalize_extension(extension)] = parser

    def get_by_extension(self, file_path: str) -> BaseParser | None:
        extension = Path(file_path).suffix
        if not extension:
            return None
        return self._parsers_by_extension.get(self._normalize_extension(extension))

    def get_by_language(self, language: str) -> BaseParser | None:
        return self._parsers_by_language.get(self._normalize_language(language))

    @staticmethod
    def _normalize_language(language: str) -> str:
        normalized_language = language.strip().lower()
        if not normalized_language:
            raise ValueError("Parser language must be a non-empty string")
        return normalized_language

    @staticmethod
    def _normalize_extension(extension: str) -> str:
        normalized_extension = extension.strip().lower()
        if not normalized_extension:
            raise ValueError("Parser extension must be a non-empty string")
        if not normalized_extension.startswith("."):
            normalized_extension = f".{normalized_extension}"
        return normalized_extension

__all__ = ["ParserRegistry"]