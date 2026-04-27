from __future__ import annotations
from parsers.parser_registry import ParserRegistry
from parsers.python_parser import PythonParser
import pytest

def test_register_and_lookup_python_parser() -> None:
    registry = ParserRegistry()
    parser = PythonParser()

    registry.register(parser)

    assert registry.get_by_language("python") is parser
    assert registry.get_by_language("PYTHON") is parser
    assert registry.get_by_extension("example.py") is parser
    assert registry.get_by_extension("example.PYW") is parser

def test_duplicate_language_registration_is_rejected() -> None:
    registry = ParserRegistry([PythonParser()])

    with pytest.raises(ValueError, match="language 'python'"):
        registry.register(PythonParser())

def test_unknown_extension_returns_none() -> None:
    registry = ParserRegistry([PythonParser()])

    assert registry.get_by_extension("README.md") is None
    assert registry.get_by_extension("no_extension") is None

def test_example_usage_with_python_parser() -> None:
    registry = ParserRegistry([PythonParser()])
    parser = registry.get_by_extension("src/app.py")

    assert parser is not None
    assert parser.language == "python"