# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Pytest module to test the lines of wires as graphs, as circuit files store them"""

import pytest

from digsim.app._line_graph import Chain, decompose, junctions, polyline_path, wire_nodes
from digsim.app._wire_path import corner_points


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
