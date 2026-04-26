from __future__ import annotations
import pytest
from core.exceptions import ParseError
from parsers.python_parser import PythonParser


VALID_SOURCE = """\
def hello():
    return "world"
"""

INVALID_SOURCE = """\
def broken(:
    return
"""


@pytest.fixture
def parser() -> PythonParser:
    return PythonParser()


def test_language_property(parser: PythonParser) -> None:
    assert parser.language == "python"


def test_parse_valid_source_returns_tree(parser: PythonParser) -> None:
    tree = parser.parse(VALID_SOURCE, "hello.py")
    assert tree is not None
    assert tree.root_node is not None


def test_parse_valid_source_root_node_type(parser: PythonParser) -> None:
    tree = parser.parse(VALID_SOURCE, "hello.py")
    assert tree.root_node.type == "module"


def test_parse_empty_source_raises_value_error(parser: PythonParser) -> None:
    with pytest.raises(ValueError):
        parser.parse("", "empty.py")


def test_parse_whitespace_only_raises_value_error(parser: PythonParser) -> None:
    with pytest.raises(ValueError):
        parser.parse("   \n  ", "blank.py")


def test_parse_invalid_syntax_raises_parse_error(parser: PythonParser) -> None:
    with pytest.raises(ParseError):
        parser.parse(INVALID_SOURCE, "broken.py")


def test_parse_error_message_contains_file_path(parser: PythonParser) -> None:
    with pytest.raises(ParseError, match="broken.py"):
        parser.parse(INVALID_SOURCE, "broken.py")


def test_parser_is_reusable(parser: PythonParser) -> None:
    # same parser instance handles multiple files correctly
    tree1 = parser.parse(VALID_SOURCE, "a.py")
    tree2 = parser.parse(VALID_SOURCE, "b.py")
    assert tree1.root_node.type == "module"
    assert tree2.root_node.type == "module"