import pytest

from core.models.edge import CodeEdgeType
from core.models.node import CodeNodeType
from extractors.python_extractor import PythonExtractor
from parsers.python_parser import PythonParser


SOURCE = """\
class Greeter:
    pass

def callee():
    return "hi"

def caller():
    return callee()
"""

FILE_PATH = "sample.py"


@pytest.fixture
def graph():
    parser = PythonParser()
    extractor = PythonExtractor()
    tree = parser.parse(SOURCE, FILE_PATH)
    return extractor.extract(tree, SOURCE, FILE_PATH)


def test_module_node_exists(graph):
    module_node = graph.get_node("sample.py::module")

    assert module_node is not None
    assert module_node.type == CodeNodeType.MODULE
    assert module_node.name == "sample"


def test_function_nodes_extracted_correctly(graph):
    callee = graph.get_node("sample.py::callee")
    caller = graph.get_node("sample.py::caller")

    assert callee is not None
    assert callee.type == CodeNodeType.FUNCTION
    assert callee.path == FILE_PATH
    assert callee.qualified_name == "sample.py::callee"
    assert callee.start_line == 4
    assert callee.end_line == 5

    assert caller is not None
    assert caller.type == CodeNodeType.FUNCTION
    assert caller.qualified_name == "sample.py::caller"
    assert caller.start_line == 7
    assert caller.end_line == 8


def test_class_node_extracted_correctly(graph):
    class_node = graph.get_node("sample.py::Greeter")

    assert class_node is not None
    assert class_node.type == CodeNodeType.CLASS
    assert class_node.path == FILE_PATH
    assert class_node.qualified_name == "sample.py::Greeter"
    assert class_node.start_line == 1
    assert class_node.end_line == 2


def test_defines_edges_exist_between_module_and_top_level_definitions(graph):
    module_id = "sample.py::module"

    assert graph.find_edges(
        edge_type=CodeEdgeType.DEFINES,
        source_id=module_id,
        target_id="sample.py::Greeter",
    )
    assert graph.find_edges(
        edge_type=CodeEdgeType.DEFINES,
        source_id=module_id,
        target_id="sample.py::callee",
    )
    assert graph.find_edges(
        edge_type=CodeEdgeType.DEFINES,
        source_id=module_id,
        target_id="sample.py::caller",
    )


def test_calls_edge_exists_between_caller_and_callee(graph):
    edges = graph.find_edges(
        edge_type=CodeEdgeType.CALLS,
        source_id="sample.py::caller",
        target_id="sample.py::callee",
    )

    assert len(edges) == 1
    assert edges[0].id == "call::sample.py::caller::sample.py::callee"


def test_node_count_is_correct(graph):
    assert graph.node_count == 4


def test_function_raw_source_is_not_empty(graph):
    callee = graph.get_node("sample.py::callee")

    assert callee is not None
    assert callee.raw_source is not None
    assert callee.raw_source.strip() != ""
    assert "def callee" in callee.raw_source
