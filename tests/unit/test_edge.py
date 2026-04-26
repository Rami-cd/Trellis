import pytest
from core.models.edge import CodeEdge, CodeEdgeType


def test_create_valid_edge():
    edge = CodeEdge(
        id="e1",
        source_id="n1",
        target_id="n2",
        type=CodeEdgeType.CALLS,
    )

    assert edge.source_id == "n1"
    assert edge.target_id == "n2"


def test_invalid_edge_missing_ids():
    with pytest.raises(ValueError):
        CodeEdge(
            id="",
            source_id="n1",
            target_id="n2",
            type=CodeEdgeType.CALLS,
        )

def test_edge_rejects_empty_source_id():
    with pytest.raises(ValueError):
        CodeEdge(id="e1", source_id="", target_id="n2", type=CodeEdgeType.CALLS)

def test_edge_rejects_empty_target_id():
    with pytest.raises(ValueError):
        CodeEdge(id="e1", source_id="n1", target_id="  ", type=CodeEdgeType.CALLS)

def test_edge_strips_whitespace():
    edge = CodeEdge(id="  e1  ", source_id="  n1  ", 
                    target_id="  n2  ", type=CodeEdgeType.CALLS)
    assert edge.id == "e1"
    assert edge.source_id == "n1"
    assert edge.target_id == "n2"

def test_edge_default_attributes_are_independent():
    e1 = CodeEdge(id="e1", source_id="n1", target_id="n2", type=CodeEdgeType.CALLS)
    e2 = CodeEdge(id="e2", source_id="n1", target_id="n2", type=CodeEdgeType.IMPORTS)
    e1.attributes["key"] = "value"
    assert "key" not in e2.attributes