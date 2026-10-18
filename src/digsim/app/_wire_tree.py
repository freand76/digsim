# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""
The wire trees in the GUI
(kept free from Qt imports so that it can be tested without a display)

An output port can drive many input ports. Each input port has its own wire, with a path
(see digsim.app._wire_path), that starts at the output port or at an inner corner of
another wire from the same output port: a branch. The wires of one output port form a
tree, with the wire that starts at the port as its root.

A wire is known by a key (the input port it drives), and the branches map the key of a
branch to the key of the wire it starts on (its parent) and the corner it starts at.
"""

from collections.abc import Callable, Hashable
from typing import TypeVar

from ._wire_path import Point, join_paths


K = TypeVar("K", bound=Hashable)


def children(branches: dict[K, tuple[K, int]], wire: K) -> list[K]:
    """The wires that start on a wire"""
    return [child for child, (parent, _) in branches.items() if parent == wire]


def descendants(branches: dict[K, tuple[K, int]], wire: K) -> list[K]:
    """The wires that start on a wire, and the wires that start on those, and so on"""
    found: list[K] = []
    todo = children(branches, wire)
    while todo:
        child = todo.pop()
        found.append(child)
        todo += children(branches, child)
    return found


def root(branches: dict[K, tuple[K, int]], wire: K) -> K:
    """The wire of a tree that starts at the output port"""
    while wire in branches:
        wire = branches[wire][0]
    return wire


def route(branches: dict[K, tuple[K, int]], wire: K) -> dict[K, int | None]:
    """
    The way from the output port to the input port of a wire: the wire itself (None, all
    its segments) and the number of segments, from the start, of each wire it starts on
    """
    segments: dict[K, int | None] = {wire: None}
    while wire in branches:
        wire, corner = branches[wire]
        # Corner k is at the end of segment k - 1
        segments[wire] = corner
    return segments


def sinks_through(branches: dict[K, tuple[K, int]], wire: K, segment: int) -> list[K]:
    """
    The wires whose way to their input port runs through a segment of a wire: the wire
    itself, and the branches (with their branches) that start after the segment
    """
    sinks = [wire]
    for child in children(branches, wire):
        if branches[child][1] > segment:
            sinks += [child, *descendants(branches, child)]
    return sinks


def selection(branches: dict[K, tuple[K, int]], wire: K, segment: int) -> dict[K, int]:
    """
    The part of a tree that a click on a segment of a wire selects: the wires through the
    segment (see sinks_through) from the closest split before the segment, where a branch
    starts on the wire or where the wire starts. It is the part that goes when the wires
    are removed. The first selected segment of each wire, the rest of it is selected too.
    """
    kids = children(branches, wire)
    splits = [branches[child][1] for child in kids if branches[child][1] <= segment]
    # Corner k is where segment k starts
    selected = {wire: max(splits, default=0)}
    for sink in sinks_through(branches, wire, segment):
        if sink != wire:
            selected[sink] = 0
    return selected


def tree(branches: dict[K, tuple[K, int]], wire: K) -> list[K]:
    """All wires of the tree that a wire belongs to"""
    top = root(branches, wire)
    return [top, *descendants(branches, top)]


def without_cycles(branches: dict[K, tuple[K, int]]) -> dict[K, tuple[K, int]]:
    """
    The branches, without the ones that would make a wire start on itself (a broken
    file): such a wire starts at the output port instead
    """
    valid = dict(branches)
    for wire in branches:
        seen = {wire}
        parent = valid.get(wire)
        while parent is not None:
            if parent[0] in seen:
                del valid[wire]
                break
            seen.add(parent[0])
            parent = valid.get(parent[0])
    return valid


def remove_wires(
    branches: dict[K, tuple[K, int]],
    paths: dict[K, list[float]],
    removed: list[K],
    corner_point: Callable[[K, int], Point],
) -> None:
    """
    Remove wires from a tree, and keep the wires that start on them. The branch that starts
    furthest along a removed wire takes its place: it gets the removed wire's path up to
    where it started, and the other branches start on it instead. 'corner_point' gives the
    position of a corner of a wire, with the branches and paths as they are when called.
    """
    for wire in removed:
        if wire not in paths:
            continue
        kids = children(branches, wire)
        if kids:
            heir = max(kids, key=lambda child: branches[child][1])
            corner = branches[heir][1]
            heir_path = paths[heir]
            paths[heir] = join_paths(paths[wire], corner, corner_point(wire, corner), heir_path)
            # The heir's corners come after the removed wire's corners now
            added = len(paths[heir]) - len(heir_path)
            for child in children(branches, heir):
                branches[child] = (heir, branches[child][1] + added)
            if wire in branches:
                branches[heir] = branches[wire]
            else:
                del branches[heir]
            # The corners before the heir's start are where they were on the removed wire
            for child in kids:
                if child != heir:
                    branches[child] = (heir, branches[child][1])
        del paths[wire]
        branches.pop(wire, None)
