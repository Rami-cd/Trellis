from core.models.graph import ProjectGraph
from core.models.node import CodeNode, CodeNodeType
from core.models.edge import CodeEdge, CodeEdgeType
import pytest


def make_node(id):
    return CodeNode(id=id, type=CodeNodeType.FUNCTION, name=id)


def test_add_and_get_node():
    graph = ProjectGraph()
    node = make_node("n1")

    graph.add_node(node)

    assert graph.get_node("n1") == node


def test_add_node_replace_true_replaces_existing_node():
    graph = ProjectGraph()
    original = CodeNode(id="n1", type=CodeNodeType.FUNCTION, name="old")
    replacement = CodeNode(
        id="n1",
        type=CodeNodeType.CLASS,
        name="new",
        language="python",
    )

    graph.add_node(original)
    graph.add_node(replacement, replace=True)

    stored = graph.get_node("n1")
    assert stored == replacement


def test_add_edge_requires_nodes():
    graph = ProjectGraph()

    edge = CodeEdge(
        id="e1",
        source_id="n1",
        target_id="n2",
        type=CodeEdgeType.CALLS,
    )

    with pytest.raises(ValueError):
        graph.add_edge(edge)


def test_add_edge_replace_true_replaces_existing_edge():
    graph = ProjectGraph()
    n1 = make_node("n1")
    n2 = make_node("n2")
    n3 = make_node("n3")

    graph.add_nodes([n1, n2, n3])
    graph.add_edge(
        CodeEdge(
            id="e1",
            source_id="n1",
            target_id="n2",
            type=CodeEdgeType.CALLS,
        )
    )

    graph.add_edge(
        CodeEdge(
            id="e1",
            source_id="n1",
            target_id="n3",
            type=CodeEdgeType.IMPORTS,
        ),
        replace=True,
    )

    stored = graph.get_edge("e1")
    assert stored is not None
    assert stored.target_id == "n3"
    assert stored.type == CodeEdgeType.IMPORTS
    assert graph.outgoing_edges("n1")[0].target_id == "n3"
    assert graph.incoming_edges("n2") == []


def test_remove_node_removes_connected_edges():
    graph = ProjectGraph()

    n1 = make_node("n1")
    n2 = make_node("n2")

    graph.add_nodes([n1, n2])

    edge = CodeEdge(
        id="e1",
        source_id="n1",
        target_id="n2",
        type=CodeEdgeType.CALLS,
    )

    graph.add_edge(edge)

    graph.remove_node("n1")

    assert graph.get_edge("e1") is None


def test_remove_edge_standalone():
    graph = ProjectGraph()
    n1 = make_node("n1")
    n2 = make_node("n2")

    graph.add_nodes([n1, n2])
    edge = CodeEdge(
        id="e1",
        source_id="n1",
        target_id="n2",
        type=CodeEdgeType.CALLS,
    )

    graph.add_edge(edge)

    removed = graph.remove_edge("e1")

    assert removed == edge
    assert graph.get_edge("e1") is None
    assert graph.outgoing_edges("n1") == []
    assert graph.incoming_edges("n2") == []


def test_neighbors_outgoing():
    graph = ProjectGraph()

    n1 = make_node("n1")
    n2 = make_node("n2")

    graph.add_nodes([n1, n2])

    graph.add_edge(CodeEdge(
        id="e1",
        source_id="n1",
        target_id="n2",
        type=CodeEdgeType.CALLS,
    ))

    neighbors = graph.neighbors("n1")

    assert len(neighbors) == 1
    assert neighbors[0].id == "n2"


def test_neighbors_incoming():
    graph = ProjectGraph()
    n1 = make_node("n1")
    n2 = make_node("n2")

    graph.add_nodes([n1, n2])
    graph.add_edge(
        CodeEdge(
            id="e1",
            source_id="n1",
            target_id="n2",
            type=CodeEdgeType.CALLS,
        )
    )

    neighbors = graph.neighbors("n2", direction="incoming")

    assert len(neighbors) == 1
    assert neighbors[0].id == "n1"


def test_neighbors_both_combines_incoming_and_outgoing_without_duplicates():
    graph = ProjectGraph()
    n1 = make_node("n1")
    n2 = make_node("n2")
    n3 = make_node("n3")

    graph.add_nodes([n1, n2, n3])
    graph.add_edges(
        [
            CodeEdge(
                id="e1",
                source_id="n1",
                target_id="n2",
                type=CodeEdgeType.CALLS,
            ),
            CodeEdge(
                id="e2",
                source_id="n2",
                target_id="n3",
                type=CodeEdgeType.IMPORTS,
            ),
            CodeEdge(
                id="e3",
                source_id="n3",
                target_id="n2",
                type=CodeEdgeType.DEFINES,
            ),
        ]
    )

    neighbors = graph.neighbors("n2", direction="both")

    assert [node.id for node in neighbors] == ["n3", "n1"]


def test_node_and_edge_count_properties():
    graph = ProjectGraph()
    n1 = make_node("n1")
    n2 = make_node("n2")

    graph.add_nodes([n1, n2])
    graph.add_edge(
        CodeEdge(
            id="e1",
            source_id="n1",
            target_id="n2",
            type=CodeEdgeType.CALLS,
        )
    )

    assert graph.node_count == 2
    assert graph.edge_count == 1


def test_find_nodes_filters_by_fields_and_attributes():
    graph = ProjectGraph()
    graph.add_nodes(
        [
            CodeNode(
                id="f1",
                type=CodeNodeType.FUNCTION,
                name="main",
                language="python",
                path="app.py",
                qualified_name="app.main",
                attributes={"visibility": "public"},
            ),
            CodeNode(
                id="c1",
                type=CodeNodeType.CLASS,
                name="Main",
                language="python",
                path="app.py",
                qualified_name="app.Main",
                attributes={"visibility": "public"},
            ),
            CodeNode(
                id="f2",
                type=CodeNodeType.FUNCTION,
                name="main",
                language="javascript",
                path="app.js",
                qualified_name="app.main",
                attributes={"visibility": "private"},
            ),
        ]
    )

    matches = graph.find_nodes(
        node_type=CodeNodeType.FUNCTION,
        language="python",
        path="app.py",
        name="main",
        qualified_name="app.main",
        attributes={"visibility": "public"},
    )

    assert [node.id for node in matches] == ["f1"]


def test_find_edges_filters_by_fields_and_attributes():
    graph = ProjectGraph()
    n1 = make_node("n1")
    n2 = make_node("n2")
    n3 = make_node("n3")

    graph.add_nodes([n1, n2, n3])
    graph.add_edges(
        [
            CodeEdge(
                id="e1",
                source_id="n1",
                target_id="n2",
                type=CodeEdgeType.CALLS,
                attributes={"confidence": "high"},
            ),
            CodeEdge(
                id="e2",
                source_id="n1",
                target_id="n3",
                type=CodeEdgeType.CALLS,
                attributes={"confidence": "low"},
            ),
            CodeEdge(
                id="e3",
                source_id="n2",
                target_id="n3",
                type=CodeEdgeType.IMPORTS,
                attributes={"confidence": "high"},
            ),
        ]
    )

    matches = graph.find_edges(
        edge_type=CodeEdgeType.CALLS,
        source_id="n1",
        target_id="n2",
        attributes={"confidence": "high"},
    )

    assert [edge.id for edge in matches] == ["e1"]
