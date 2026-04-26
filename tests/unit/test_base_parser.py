import pytest
from parsers.base_parser import BaseParser

def test_base_parser_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        BaseParser() # type: ignore[abstract]

def test_concrete_subclass_must_implement_parse_and_language():
    class MissingParseParser(BaseParser):
        @property
        def language(self) -> str:
            return "python"

    class MissingLanguageParser(BaseParser):
        def parse(self, source: str, file_path: str):
            return {"source": source, "file_path": file_path}

    with pytest.raises(TypeError):
        MissingParseParser() # type: ignore[abstract]

    with pytest.raises(TypeError):
        MissingLanguageParser() # type: ignore[abstract]