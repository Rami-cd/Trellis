import pytest
from core.models.node import CodeNode, CodeNodeType


def test_create_valid_node():
    node = CodeNode(
        id="n1",
        type=CodeNodeType.FUNCTION,
        name="my_func",
        language="python",
    )

    assert node.id == "n1"
    assert node.name == "my_func"


def test_node_strips_whitespace():
    node = CodeNode(
        id="  n1  ",
        type=CodeNodeType.CLASS,
        name="  MyClass  ",
    )

    assert node.id == "n1"
    assert node.name == "MyClass"


def test_invalid_empty_id():
    with pytest.raises(ValueError):
        CodeNode(
            id="",
            type=CodeNodeType.FUNCTION,
            name="x",
        )


def test_invalid_line_numbers():
    with pytest.raises(ValueError):
        CodeNode(
            id="n1",
            type=CodeNodeType.FUNCTION,
            name="x",
            start_line=10,
            end_line=5,
        )

def test_node_rejects_empty_name():
    with pytest.raises(ValueError):
        CodeNode(id="n1", type=CodeNodeType.FUNCTION, name="  ")

def test_node_default_attributes_are_independent():
    # ensures field(default_factory=dict) works correctly
    # two nodes must not share the same dict instance
    n1 = CodeNode(id="n1", type=CodeNodeType.FUNCTION, name="a")
    n2 = CodeNode(id="n2", type=CodeNodeType.FUNCTION, name="b")
    n1.attributes["key"] = "value"
    assert "key" not in n2.attributes