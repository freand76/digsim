# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Pytest module to test the wire trees in the GUI"""

from digsim.app._wire_path import corner_points
from digsim.app._wire_tree import (
    children,
    descendants,
    remove_wires,
    root,
    route,
    selection,
    sinks_through,
    tree,
    without_cycles,
)


# a starts at the output port, b and c start on a (b furthest along), d starts on b
BRANCHES = {"b": ("a", 3), "c": ("a", 1), "d": ("b", 2)}


def test_tree_structure():
    """The wires of a tree, from any of them"""
    assert sorted(children(BRANCHES, "a")) == ["b", "c"]
    assert sorted(descendants(BRANCHES, "a")) == ["b", "c", "d"]
    assert root(BRANCHES, "d") == "a"
    assert sorted(tree(BRANCHES, "c")) == ["a", "b", "c", "d"]
    assert sorted(tree({}, "x")) == ["x"]


def test_route():
    """The way from the output port to an input port, over the wires it starts on"""
    assert route(BRANCHES, "d") == {"d": None, "b": 2, "a": 3}
    assert route(BRANCHES, "a") == {"a": None}


def test_sinks_through():
    """A segment carries the signal to its own input port and those of later branches"""
    # Segment 0 of a is before both branches, segment 2 only before b (corner 3)
    assert sorted(sinks_through(BRANCHES, "a", 0)) == ["a", "b", "c", "d"]
    assert sorted(sinks_through(BRANCHES, "a", 2)) == ["a", "b", "d"]
    assert sorted(sinks_through(BRANCHES, "a", 3)) == ["a"]
    assert sorted(sinks_through(BRANCHES, "b", 1)) == ["b", "d"]
    assert sorted(sinks_through(BRANCHES, "d", 0)) == ["d"]


def test_selection():
    """A click selects from the closest split before the clicked segment, and all after it"""
    # b starts at corner 3 of a and c at corner 1, so a has splits at corners 1 and 3
    assert selection(BRANCHES, "a", 0) == {"a": 0, "b": 0, "c": 0, "d": 0}
    assert selection(BRANCHES, "a", 2) == {"a": 1, "b": 0, "d": 0}
    assert selection(BRANCHES, "a", 3) == {"a": 3}
    assert selection(BRANCHES, "a", 5) == {"a": 3}
    # A branch from where it starts, d starts at corner 2 of b
    assert selection(BRANCHES, "b", 1) == {"b": 0, "d": 0}
    assert selection(BRANCHES, "b", 2) == {"b": 2}
    assert selection(BRANCHES, "d", 0) == {"d": 0}


def test_without_cycles():
    """Wires that would start on themselves start at the output port instead"""
    assert without_cycles(BRANCHES) == BRANCHES
    broken = {"a": ("b", 1), "b": ("a", 1), "c": ("b", 1)}
    valid = without_cycles(broken)
    # One of a and b starts at the port, and the rest of the tree is kept
    assert len(valid) == 2
    assert root(valid, "c") in ("a", "b")


def _tree_geometry():
    """
    A wire a from (0, 0) to (200, 100), with b starting at its corner 3 and c at its
    corner 1, d at corner 1 of b, and the position of each corner of each wire
    """
    paths = {"a": [50, 30, 150], "b": [180], "c": [80], "d": [250]}
    branches = {"b": ("a", 3), "c": ("a", 1), "d": ("b", 1)}
    dests = {"a": (200, 100), "b": (300, -50), "c": (120, 60), "d": (350, 0)}

    def points(wire):
        if wire in branches:
            parent, corner = branches[wire]
            start = points(parent)[corner]
        else:
            start = (0, 0)
        return corner_points(start, dests[wire], paths[wire])

    return paths, branches, points


def test_remove_wire_keeps_branches():
    """The branch furthest along takes the place of a removed wire, the others move to it"""
    paths, branches, points = _tree_geometry()
    before = {wire: points(wire) for wire in ("b", "c", "d")}
    remove_wires(branches, paths, ["a"], lambda wire, corner: points(wire)[corner])
    assert sorted(paths) == ["b", "c", "d"]
    # d starts at the same corner of b, which comes after a's corners now
    assert branches == {"c": ("b", 1), "d": ("b", 3)}
    # Both wires look the same as before (b now from the output port)
    assert points("b")[-len(before["b"]) + 1 :] == before["b"][1:]
    assert points("b")[:3] == [(0, 0), (50, 0), (50, 30)]
    assert points("c") == before["c"]
    assert points("d") == before["d"]


def test_remove_branch_and_leaf():
    """Removing wires without branches leaves the rest of the tree as it was"""
    paths, branches, points = _tree_geometry()
    remove_wires(branches, paths, ["b", "c", "d"], lambda wire, corner: points(wire)[corner])
    assert paths == {"a": [50, 30, 150]}
    assert branches == {}
    paths, branches, points = _tree_geometry()
    remove_wires(branches, paths, ["a", "b", "c", "d"], lambda wire, corner: points(wire)[corner])
    assert paths == {}
    assert branches == {}
