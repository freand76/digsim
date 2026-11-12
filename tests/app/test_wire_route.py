# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""Pytest module to test the wires to the ports of rotated components"""

import pytest

from digsim.app._wire_path import corner_points
from digsim.app._wire_route import automatic_route, clicked_route, rotated


def _points(start, end, path):
    """The corners of a wire, without the segments without length"""
    points = []
    for point in corner_points(start, end, path):
        if not points or point != points[-1]:
            points.append(point)
    return points


def _turns_back(points):
    """Does a route go back the way it came"""
    for first, middle, last in zip(points, points[1:], points[2:]):
        way_in = (middle[0] - first[0], middle[1] - first[1])
        way_out = (last[0] - middle[0], last[1] - middle[1])
        if way_in[0] * way_out[0] < 0 or way_in[1] * way_out[1] < 0:
            return True
    return False


@pytest.mark.parametrize(
    ("direction", "rotation", "result"),
    [("right", 90, "down"), ("left", 90, "up"), ("up", 90, "right"), ("right", 270, "up")],
)
def test_rotated(direction, rotation, result):
    """Clockwise, on the screen"""
    assert rotated(direction, rotation) == result


def test_down_into_a_port_that_faces_up():
    start, end = (0, 0), (100, 100)
    path = automatic_route(start, "right", end, "up")
    assert _points(start, end, path) == [(0, 0), (100, 0), (100, 100)]


def test_around_to_a_port_that_faces_up():
    """From below the port, the wire comes down into it from above"""
    start, end = (0, 200), (100, 100)
    rect = (80, 100, 40, 40)
    points = _points(start, end, automatic_route(start, "right", end, "up", [rect]))
    assert points[-2:] == [(100, 90), (100, 100)]
    assert not _turns_back(points)


def test_from_a_port_that_faces_down():
    """The path leaves the port up or down: across without length first"""
    start, end = (0, 0), (100, 100)
    path = automatic_route(start, "down", end, "left")
    assert path == [0]
    assert _points(start, end, path) == [(0, 0), (0, 100), (100, 100)]


def test_backwards_around_the_components():
    """From an output that faces left, to an input to its right that faces right"""
    start, end = (0, 0), (100, 0)
    rects = [(0, -20, 40, 40), (100, -20, 40, 40)]
    points = _points(start, end, automatic_route(start, "left", end, "right", rects))
    assert points == [(0, 0), (-10, 0), (-10, -35), (110, -35), (110, 0), (100, 0)]


def test_straight_between_ports_that_face_each_other():
    start, end = (0, 0), (-100, 0)
    rects = [(0, -20, 40, 40), (-140, -20, 40, 40)]
    path = automatic_route(start, "left", end, "right", rects)
    assert _points(start, end, path) == [(0, 0), (-100, 0)]


def test_clicked_from_a_port_that_faces_up():
    """Up first, then across to the click, then to the input. The click is a corner."""
    start, end = (0, 0), (100, 0)
    path = clicked_route(start, "up", end, "left", [(50, -50)])
    assert _points(start, end, path) == [
        (0, 0),
        (0, -50),
        (50, -50),
        (90, -50),
        (90, 0),
        (100, 0),
    ]


def test_clicked_from_the_input():
    """Drawn from the input, the wire reaches the output that faces up from above"""
    start, end = (0, 0), (100, 0)
    path = clicked_route(start, "up", end, "left", [(50, -50)], from_source=False)
    assert _points(start, end, path) == [(0, 0), (0, -50), (50, -50), (50, 0), (100, 0)]
