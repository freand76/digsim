# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""Pytest module to test the lines of wires as graphs, as circuit files store them"""

import pytest

from digsim.app._line_graph import (
    Chain,
    align_to_ports,
    decompose,
    junctions,
    polyline_path,
    wire_nodes,
    without_ports,
)
from digsim.app._wire_path import corner_points
from digsim.storage_model import LineDataClass


def test_wire_nodes():
    """The ends, the turns and the anchors are nodes, a straight run is one segment"""
    points = [(0, 0), (50, 0), (100, 0), (100, 0), (100, 40), (140, 40)]
    assert wire_nodes(points, set()) == [[0], [2, 3], [4], [5]]
    # A wire starts at corner 1, on the straight run
    assert wire_nodes(points, {1}) == [[0], [1], [2, 3], [4], [5]]


def test_wire_nodes_keep_a_way_back():
    """A wire that goes back the way it came turns there"""
    points = [(0, 0), (60, 0), (60, 0), (40, 0), (40, 30), (80, 30)]
    assert [points[place[0]] for place in wire_nodes(points, set())] == [
        (0, 0),
        (60, 0),
        (40, 0),
        (40, 30),
        (80, 30),
    ]


@pytest.mark.parametrize(
    "points, keep, path, kept",
    [
        # Across, up or down, and across to the end
        ([(0, 0), (50, 0), (50, 40), (100, 40)], set(), [50], {}),
        # Straight across
        ([(0, 0), (100, 0)], set(), [100], {}),
        # A point on a straight run that is kept: a corner (a joint) there
        ([(0, 0), (30, 0), (50, 0), (50, 40), (100, 40)], {1}, [30, 0, 50], {1: 1}),
        # Up or down first: across without length from the start
        ([(0, 0), (0, 40), (100, 40)], set(), [0], {}),
        # Not straight: across first, then up or down
        ([(0, 0), (60, 30), (100, 30)], set(), [60], {}),
        # A kept point where the wire turns
        ([(0, 0), (50, 0), (50, 40), (100, 40)], {2}, [50], {2: 2}),
    ],
)
def test_polyline_path(points, keep, path, kept):
    """The path through the points of a graph, that the GUI draws the wire with"""
    result, corners = polyline_path(points, keep)
    assert result == path
    assert corners == kept
    drawn = corner_points(points[0], points[-1], result)
    for index, corner in corners.items():
        assert drawn[corner] == points[index]


def test_polyline_path_goes_back():
    """A wire that goes back the way it came keeps the way back"""
    points = [(0, 0), (60, 0), (40, 0), (40, 30), (80, 30)]
    path, _ = polyline_path(points, set())
    drawn = corner_points(points[0], points[-1], path)
    assert (60, 0) in drawn


PLACES = {
    "A.O": (0, 0),
    "B.O": (0, 100),
    "L1.I": (200, 0),
    "L2.I": (200, 100),
    "1": (100, 0),
    "2": (100, 100),
    "3": (100, 50),
}


def test_decompose_a_tree():
    """From the output port to a port, and the branches from where wires meet"""
    segments = [("A.O", "1"), ("1", "L1.I"), ("1", "3"), ("3", "2"), ("2", "L2.I")]
    ports = ["A.O", "L1.I", "L2.I"]
    chains = decompose(ports, {"A.O"}, PLACES, segments)
    assert chains == [Chain(["A.O", "1", "L1.I"], None), Chain(["1", "3", "2", "L2.I"], 0)]


def test_decompose_two_outputs():
    """A second output port of the line is reached by a branch"""
    segments = [("A.O", "1"), ("1", "L1.I"), ("1", "3"), ("3", "2"), ("2", "B.O")]
    chains = decompose(["A.O", "B.O", "L1.I"], {"A.O", "B.O"}, PLACES, segments)
    assert chains == [Chain(["A.O", "1", "L1.I"], None), Chain(["1", "3", "2", "B.O"], 0)]


def test_decompose_cuts_a_loop_and_loose_ends():
    """A line connects its ports once: a loop is cut, and a loose end goes"""
    segments = [
        ("A.O", "L1.I"),
        ("A.O", "1"),
        ("1", "L1.I"),
        # A loose end
        ("2", "3"),
        ("3", "L2.I"),
    ]
    chains = decompose(["A.O", "L1.I", "L2.I"], {"A.O"}, PLACES, segments)
    assert chains == [Chain(["A.O", "L1.I"], None)]


def test_decompose_ports_of_the_same_kind():
    """A line of two input ports: from one to the other"""
    chains = decompose(["L1.I", "L2.I"], set(), PLACES, [("L1.I", "1"), ("1", "2"), ("2", "L2.I")])
    assert chains == [Chain(["L1.I", "1", "2", "L2.I"], None)]


def test_junctions():
    """A dot where the line goes three or more ways: not at a corner or on a straight run"""
    # A corner, and a branch that leaves the corner along one of its ways
    corner = [((0, 0), (50, 0)), ((50, 0), (50, 40)), ((50, 0), (50, 20))]
    assert junctions(corner) == []
    # A branch from a straight run
    tee = [((0, 0), (50, 0)), ((50, 0), (100, 0)), ((50, 0), (50, 40))]
    assert junctions(tee) == [(50, 0)]
    # A wire that ends on another one, between its corners
    end_on = [((0, 0), (100, 0)), ((50, 40), (50, 0))]
    assert junctions(end_on) == [(50, 0)]
    # Two wires that run together and split where the second one turns
    split = [((0, 0), (0, 100)), ((0, 0), (0, 60)), ((0, 60), (40, 60))]
    assert junctions(split) == [(0, 60)]
    # Without length: no way
    assert junctions([((0, 0), (50, 0)), ((50, 0), (50, 0)), ((50, 0), (90, 0))]) == []


def _tree():
    """A.O to a junction (1), from there to L1.I, and around a corner (2) to L2.I"""
    return LineDataClass(
        ports=["A.O", "L1.I", "L2.I"],
        points={"1": [100, 0], "2": [100, 100]},
        segments=[["A.O", "1"], ["1", "L1.I"], ["1", "2"], ["2", "L2.I"]],
    )


def test_without_ports_cuts_back_to_the_junction():
    assert without_ports([_tree()], {"L2.I"}) == [
        LineDataClass(
            ports=["A.O", "L1.I"], points={"1": [100, 0]}, segments=[["A.O", "1"], ["1", "L1.I"]]
        )
    ]


def test_without_ports_keeps_the_rest_of_the_line():
    (line,) = without_ports([_tree()], {"A.O"})
    assert line.ports == ["L1.I", "L2.I"]
    assert line.segments == [["1", "L1.I"], ["1", "2"], ["2", "L2.I"]]


def test_without_ports_drops_a_line_with_one_port():
    assert without_ports([_tree()], {"L1.I", "L2.I"}) == []


def test_without_ports_keeps_other_lines():
    other = LineDataClass(ports=["B.O", "L3.I"], segments=[["B.O", "L3.I"]])
    lines = without_ports([_tree(), other], {"L2.I"})
    assert lines[1] is other


def test_without_ports_keeps_a_port_without_segments():
    line = _tree()
    line.ports.append("L3.I")
    (result,) = without_ports([line], {"L2.I"})
    assert result.ports == ["A.O", "L1.I", "L3.I"]


def test_align_to_ports():
    """
    A port that moved up: a step close to it, to its corner, which stays where it was
    """
    places = {"A.O": (40, 20), "p1": (100, 40), "p2": (100, 100), "B.I": (200, 100)}
    segments = [("A.O", "p1"), ("p1", "p2"), ("p2", "B.I")]
    segments = align_to_ports(places, {"A.O", "B.I"}, segments)
    assert segments == [
        ("A.O", "A.O~p1~0"),
        ("A.O~p1~0", "A.O~p1~1"),
        ("A.O~p1~1", "p1"),
        ("p1", "p2"),
        ("p2", "B.I"),
    ]
    assert places["A.O~p1~0"] == (50, 20)
    assert places["A.O~p1~1"] == (50, 40)
    assert places["p1"] == (100, 40)


def test_align_to_ports_close():
    """A corner close to the port gets the step half way"""
    places = {"A.O": (40, 20), "p1": (46, 40), "B.I": (46, 100)}
    segments = align_to_ports(places, {"A.O", "B.I"}, [("p1", "A.O"), ("p1", "B.I")])
    assert len(segments) == 4
    assert places["A.O~p1~0"] == (43, 20)


def test_align_to_ports_lined_up():
    """A line whose points line up with its ports, and a vertical segment, stay"""
    places = {"A.O": (40, 20), "p1": (100, 20), "p2": (100, 100), "B.I": (100, 140)}
    segments = [("A.O", "p1"), ("p1", "p2"), ("p2", "B.I")]
    before = dict(places)
    assert align_to_ports(places, {"A.O", "B.I"}, segments) == segments
    assert places == before
