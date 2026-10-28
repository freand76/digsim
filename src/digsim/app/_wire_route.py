# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""
The shape of a wire to a port of a rotated component
(kept free from Qt imports so that it can be tested without a display)

A wire leaves an output port to the right and reaches an input port from the left, unless
the component is rotated: then a port faces right, down, left or up, its direction. The
wires to such a port are routed here, as points from port to port that become a path (see
digsim.app._wire_path and _line_graph.polyline_path). The path of a wire that leaves a
port up or down starts with a segment without length across.

A wire can also start or end at a corner of another wire, which has no direction: it
leaves the corner across or up or down, but not along the other wire, the directions
that are taken there (see corner_directions).
"""

import math
from collections.abc import Sequence
from itertools import pairwise

from digsim.app._line_graph import polyline_path
from digsim.app._wire_path import WIRE_TO_COMPONENT_DIST, X_OFFSET, Point, Rect, exits_vertically


# The directions clockwise, and their steps
DIRECTIONS = ["right", "down", "left", "up"]
STEPS = {"right": (1, 0), "down": (0, 1), "left": (-1, 0), "up": (0, -1)}
_BACKWARDS = {"right": "left", "left": "right", "up": "down", "down": "up"}
# How bad a route is: going back on itself, through a component, and each corner
_BACK = 1000
_THROUGH = 100
_CORNER = 10


def default_direction(is_output: bool) -> str:
    """The direction of a port of a component that isn't rotated"""
    return "right" if is_output else "left"


def rotated(direction: str, rotation: int) -> str:
    """A direction turned clockwise by a rotation of 0, 90, 180 or 270 degrees"""
    return DIRECTIONS[(DIRECTIONS.index(direction) + rotation // 90) % 4]


def faces_vertically(direction: str) -> bool:
    """True for up and down"""
    return direction in ("up", "down")


def stub(point: Point, direction: str, length: float = X_OFFSET) -> Point:
    """The point at a distance from a port, in its direction"""
    step_x, step_y = STEPS[direction]
    return point[0] + step_x * length, point[1] + step_y * length


def _toward(start: Point, end: Point) -> str | None:
    if end[0] != start[0]:
        return "right" if end[0] > start[0] else "left"
    if end[1] != start[1]:
        return "down" if end[1] > start[1] else "up"
    return None


def _through(start: Point, end: Point, rect: Rect) -> bool:
    """Does a segment run through the inside of a rect"""
    left, top, width, height = rect
    return (
        max(start[0], end[0]) > left + 1
        and min(start[0], end[0]) < left + width - 1
        and max(start[1], end[1]) > top + 1
        and min(start[1], end[1]) < top + height - 1
    )


def _simplified(points: list[Point]) -> list[Point]:
    """Without repeated points, and without points on a straight run"""
    result: list[Point] = []
    for point in points:
        if result and point == result[-1]:
            continue
        if len(result) >= 2 and _toward(result[-2], result[-1]) == _toward(result[-1], point):
            result[-1] = point
            continue
        result.append(point)
    return result


def _cost(points: list[Point], rects: Sequence[Rect], taken: tuple[set[str], set[str]]) -> float:
    """How bad a route is, see _BACK, _THROUGH and _CORNER, then how long"""
    cost = 0.0
    ways = [_toward(first, second) for first, second in pairwise(points)]
    for way_in, way_out in pairwise(ways):
        if way_in is not None and way_out is not None and way_in != way_out:
            cost += _BACK if way_out == _BACKWARDS[way_in] else _CORNER
    # Not along another wire from a corner, at the start or at the end
    if ways and ways[0] in taken[0]:
        cost += _BACK
    if ways and ways[-1] is not None and _BACKWARDS[ways[-1]] in taken[1]:
        cost += _BACK
    # Around the components, not through them
    for start, end in pairwise(points):
        cost += sum(_THROUGH for rect in rects if _through(start, end, rect))
    length = sum(
        abs(second[0] - first[0]) + abs(second[1] - first[1]) for first, second in pairwise(points)
    )
    return cost + length / 10000


def automatic_route(
    start: Point,
    start_direction: str | None,
    end: Point,
    end_direction: str | None,
    rects: Sequence[Rect] = (),
    start_taken: set[str] | None = None,
    end_taken: set[str] | None = None,
) -> list[float]:
    """
    The path of a wire that has not been edited, from the port at 'start' that faces
    'start_direction' to the port at 'end'. A direction is None at a corner of another
    wire, with the directions 'taken' there. It leaves and reaches the ports in their
    directions, and goes around the components ('rects') with as few corners as it can.
    """
    first = start if start_direction is None else stub(start, start_direction)
    last = end if end_direction is None else stub(end, end_direction)
    middle_x = math.floor((first[0] + last[0]) / 2)
    middle_y = math.floor((first[1] + last[1]) / 2)
    middles: list[list[Point]] = [
        [(last[0], first[1])],
        [(first[0], last[1])],
        [(middle_x, first[1]), (middle_x, last[1])],
        [(first[0], middle_y), (last[0], middle_y)],
    ]
    if rects:
        margin = WIRE_TO_COMPONENT_DIST + X_OFFSET
        above = min(rect[1] for rect in rects) - margin
        below = max(rect[1] + rect[3] for rect in rects) + margin
        left = min(rect[0] for rect in rects) - margin
        right = max(rect[0] + rect[2] for rect in rects) + margin
        for y in (above, below):
            middles.append([(first[0], y), (last[0], y)])
        for x in (left, right):
            middles.append([(x, first[1]), (x, last[1])])
    taken = (start_taken or set(), end_taken or set())
    routes = [_simplified([start, first, *middle, last, end]) for middle in middles]
    best = min(routes, key=lambda points: _cost(points, rects, taken))
    return polyline_path(best, set())[0]


def _leaves_vertically(
    point: Point, direction: str | None, taken: set[str], toward: Point
) -> bool:
    if direction is not None:
        return faces_vertically(direction)
    return exits_vertically(taken, point, toward)


def _from_end(
    start: Point, direction: str | None, taken: set[str], clicks: list[Point]
) -> list[Point]:
    """
    The points from a port (or corner) through the clicks, like the wire was drawn: each
    click is the point after a bend (the odd ones)
    """
    points = [start]
    vertical = bool(clicks) and _leaves_vertically(start, direction, taken, clicks[0])
    for click_x, click_y in clicks:
        last = points[-1]
        points.append((last[0], click_y) if vertical else (click_x, last[1]))
        points.append((click_x, click_y))
    return points


def _arrival(point: Point, end: Point, direction: str | None, taken: set[str]) -> list[Point]:
    """The points from the last click to a port (or a corner), in its direction"""
    if direction is None:
        if exits_vertically(taken, end, point):
            return [(end[0], point[1]), end]
        return [(point[0], end[1]), end]
    last = stub(end, direction)
    if faces_vertically(direction):
        step_y = STEPS[direction][1]
        if (point[1] - end[1]) * step_y >= X_OFFSET:
            # On the side the port faces: across to it, and up or down to it
            return [(end[0], point[1]), end]
        return [(point[0], last[1]), (end[0], last[1]), end]
    return [(last[0], point[1]), (last[0], end[1]), end]


def clicked_route(
    start: Point,
    start_direction: str | None,
    end: Point,
    end_direction: str | None,
    clicks: list[Point],
    from_source: bool = True,
    start_taken: set[str] | None = None,
    end_taken: set[str] | None = None,
) -> list[float]:
    """
    The path of a wire drawn with clicks, from the port where the drawing started
    (the start, unless not 'from_source'): from the port in its direction, across and
    then up or down to each click (or up or down first, from a port that faces up or
    down), and then to the other port in its direction. A direction is None at a corner
    of another wire, see automatic_route().
    """
    start_taken, end_taken = start_taken or set(), end_taken or set()
    # The clicks are corners of the wire, also on a straight run
    clicked = {2 * (number + 1) for number in range(len(clicks))}
    if from_source:
        points = _from_end(start, start_direction, start_taken, clicks)
        points += _arrival(points[-1], end, end_direction, end_taken)
    else:
        # The clicks are in the order they were made, from the end
        points = _from_end(end, end_direction, end_taken, clicks)
        points += _arrival(points[-1], start, start_direction, start_taken)
        points.reverse()
        clicked = {len(points) - 1 - index for index in clicked}
    return polyline_path(points, clicked)[0]
