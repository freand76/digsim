# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""
The shape of a wire in the GUI
(kept free from Qt imports so that it can be tested without a display)

A wire runs from an output port to an input port with horizontal and vertical segments,
and starts and ends with a horizontal segment. Its shape is a path: the x position of
each vertical segment, with the y position of the horizontal segment between two
vertical segments in between, [x, y, x, ..., x]. A path can only describe such wires.

The segments are numbered from the output port: segment 0 runs horizontally from the
output port, segment k (1 to len(path)) is placed by path[k - 1] (vertical when k is odd,
horizontal when k is even), and the last segment runs horizontally into the input port.

The corners are numbered the same way: corner k is where segment k starts, so corner 0 is
the output port and the last corner is the input port. A wire can start at an inner corner
of another wire with the same source instead of at the output port, see
digsim.app._wire_tree.
"""

import math
from itertools import pairwise


Point = tuple[float, float]
# x, y, width and height
Rect = tuple[float, float, float, float]

# The distance between the wire and the source component, when the wire runs backwards
WIRE_TO_COMPONENT_DIST = 5
# The horizontal distance from a port to the first or last vertical segment, backwards
X_OFFSET = 10
# The size of the step that splitting a segment makes
SPLIT_STEP = 20


def automatic_path(source: Point, dest: Point, source_rect: Rect) -> list[float]:
    """
    The path of a wire that has not been edited. Forwards it bends halfway between the
    ports, backwards it runs around the source component. The positions are whole
    numbers, like the positions of the components and the clicks.
    """
    (source_x, source_y), (dest_x, dest_y) = source, dest
    if source_x < dest_x:
        return [math.floor((source_x + dest_x) / 2)]
    half_dist_y = (source_y + dest_y) / 2
    rect_y, rect_height = source_rect[1], source_rect[3]
    if dest_y < source_y:
        y_mid = min(rect_y - WIRE_TO_COMPONENT_DIST, half_dist_y)
    else:
        y_mid = max(rect_y + rect_height + WIRE_TO_COMPONENT_DIST, half_dist_y)
    return [round(source_x + X_OFFSET), math.floor(y_mid), round(dest_x - X_OFFSET)]


def clicked_path(
    source: Point,
    dest: Point,
    clicks: list[Point],
    from_source: bool = True,
    source_offset: float = X_OFFSET,
    vertical_first: bool = False,
) -> list[float]:
    """
    The path of a wire drawn with clicks between the ports. From the port where the
    drawing started, the wire runs horizontally to the x of each click, and then
    vertically to its y. Like it was drawn, it then runs to the x of the other port and up
    or down to it, with the last vertical segment just before the port, so that it reaches
    the port horizontally. 'from_source' is False when the drawing started at the input
    port (dest). A wire that reaches another wire there needs no 'source_offset', unless
    it would reach it along the other wire (see arrival_offset).

    A wire drawn from a corner of another wire (source) runs 'vertical_first' when it
    would leave the corner along the other wire otherwise (see exits_vertically): up or
    down to the y of each click, and then across to its x. It then reaches the port like
    it was drawn, up or down and then across.
    """
    if from_source and vertical_first:
        path = [source[0]]
        for click_x, click_y in clicks:
            path += [click_y, click_x]
        return path
    if from_source:
        path = [value for click in clicks for value in click]
        path.append(dest[0] - X_OFFSET)
        return path
    # From the input port: the clicks in reverse order, seen from the output port
    path = [source[0] + source_offset]
    for click_x, click_y in reversed(clicks):
        path += [click_y, click_x]
    return path


def is_forwards(source: Point, dest: Point) -> bool:
    """
    Does a wire run forwards, to the right from the output port: then a wire drawn without
    clicks can have one vertical segment, otherwise it would run through the component
    """
    return source[0] + X_OFFSET < dest[0]


def drawing_points(start: Point, clicks: list[Point], vertical_first: bool = False) -> list[Point]:
    """
    The corners of a wire being drawn, from the port where the drawing started through
    the clicked positions (across to the x of each, then up or down to it, or the other
    way around, 'vertical_first'). With the mouse position as the last click, this shows
    the wire as a click there will make it.
    """
    points = [start]
    for click_x, click_y in clicks:
        if vertical_first:
            points += [(points[-1][0], click_y), (click_x, click_y)]
        else:
            points += [(click_x, points[-1][1]), (click_x, click_y)]
    return points


def corner_directions(points: list[Point], corner: int) -> set[str]:
    """
    The directions ("left", "right", "up", "down") that a wire runs in from one of its
    corners: back to where it came from, and on to where it goes. At a joint, the corners
    of a segment without length, these are the two directions of the straight line.
    """
    point = points[corner]

    def direction(other: Point) -> str:
        if other[0] != point[0]:
            return "right" if other[0] > point[0] else "left"
        return "down" if other[1] > point[1] else "up"

    directions = set()
    for side in (points[corner - 1 :: -1] if corner > 0 else [], points[corner + 1 :]):
        other = next((other for other in side if other != point), None)
        if other is not None:
            directions.add(direction(other))
    return directions


def exits_vertically(taken: set[str], start: Point, toward: Point) -> bool:
    """
    Does a wire that starts at a corner of another wire leave it up or down, toward a
    point: when leaving it across would run along the other wire, in one of the 'taken'
    directions (see corner_directions)
    """
    if toward[0] == start[0]:
        return True
    return ("right" if toward[0] > start[0] else "left") in taken


def step_aside(path: list[float], start: Point, dest: Point, taken: set[str]) -> list[float]:
    """
    A path from a corner of another wire (start) that leaves it across, but then runs on
    along the other wire, at the same height ('taken', see corner_directions), gets a
    step down first instead, a split step from the other wire
    """
    points = corner_points(start, dest, path)
    other = next((point for point in points if point != start), None)
    if other is None or other[1] != start[1] or path[0] != start[0]:
        return path
    if ("right" if other[0] > start[0] else "left") not in taken:
        return path
    if len(path) == 1:
        return [path[0], start[1] + SPLIT_STEP, dest[0] - X_OFFSET]
    return [path[0], start[1] + SPLIT_STEP, *path[2:]]


def arrival_offset(taken: set[str], end: Point, coming_from: Point) -> float:
    """
    Where a wire that reaches a corner of another wire (end) coming from a point turns to
    reach it: at the corner, to reach it up or down, or a step to the side, to reach it
    across when up or down would run along the other wire ('taken', see
    corner_directions). The offset from the corner's x.
    """
    if coming_from[1] == end[1]:
        return 0
    if ("up" if coming_from[1] < end[1] else "down") not in taken:
        return 0
    return X_OFFSET if coming_from[0] >= end[0] else -X_OFFSET


def is_valid_path(path: list[float]) -> bool:
    """A path has an x position first and last, so an odd length"""
    return len(path) % 2 == 1


def corner_points(source: Point, dest: Point, path: list[float]) -> list[Point]:
    """The points of the wire: the ports and every corner in between"""
    points = [source]
    y = source[1]
    for index, value in enumerate(path):
        if index % 2 == 0:
            # A vertical segment at x = value, from the last height
            points.append((value, y))
        else:
            # A horizontal segment at y = value
            y = value
            points.append((points[-1][0], y))
    points.append((points[-1][0], dest[1]))
    points.append(dest)
    return points


def segment_count(path: list[float]) -> int:
    """The number of segments of a wire"""
    return len(path) + 2


def nearest_segment(source: Point, dest: Point, path: list[float], point: Point) -> int:
    """The segment closest to a point, like the mouse position"""
    point_x, point_y = point

    def distance(segment: tuple[Point, Point]) -> float:
        (start_x, start_y), (end_x, end_y) = segment
        dist_x = max(min(start_x, end_x) - point_x, 0, point_x - max(start_x, end_x))
        dist_y = max(min(start_y, end_y) - point_y, 0, point_y - max(start_y, end_y))
        return math.hypot(dist_x, dist_y)

    segments = list(pairwise(corner_points(source, dest, path)))
    return min(range(len(segments)), key=lambda segment: distance(segments[segment]))


def handle_at(
    source: Point, dest: Point, path: list[float], point: Point, radius: float
) -> int | None:
    """
    The movable segment whose handle, at the middle of the segment, is within 'radius'
    of a point, like the mouse position. None if there is none.
    """
    point_x, point_y = point
    segments = list(pairwise(corner_points(source, dest, path)))
    for segment, ((start_x, start_y), (end_x, end_y)) in enumerate(segments):
        if not is_movable(path, segment) or (start_x, start_y) == (end_x, end_y):
            # Segments at the ports, and segments without length, have no handle
            continue
        middle_x, middle_y = (start_x + end_x) / 2, (start_y + end_y) / 2
        if math.hypot(point_x - middle_x, point_y - middle_y) <= radius:
            return segment
    return None


def is_vertical(segment: int) -> bool:
    """True for a vertical segment, False for a horizontal"""
    return segment % 2 == 1


def is_movable(path: list[float], segment: int) -> bool:
    """All segments except the first and last, which are attached to the ports"""
    return 1 <= segment <= len(path)


def move_segment(path: list[float], segment: int, position: float) -> list[float]:
    """
    Move a segment: a vertical segment to x = position, a horizontal segment to
    y = position. The first and last segments can't be moved.
    """
    if not is_movable(path, segment):
        raise ValueError(f"Segment {segment} is attached to a port and can't be moved")
    new_path = list(path)
    new_path[segment - 1] = position
    return new_path


def split_segment(
    source: Point,
    dest: Point,
    path: list[float],
    segment: int,
    at: Point,
    step_size: float = SPLIT_STEP,
) -> list[float]:
    """
    Split a segment at the point 'at': a step of two new segments is put in between the
    two halves, so the wire stays horizontal and vertical. With a step size of 0 the wire
    keeps its shape, and gets a joint at 'at': two corners, where a branch can start.
    """
    if not 0 <= segment < segment_count(path):
        raise ValueError(f"The wire has no segment {segment}")
    at_x, at_y = at
    if segment == 0:
        # From the output port to the split, then a step down to the next segment
        return [at_x, source[1] + step_size, *path]
    if segment == len(path) + 1:
        # A step down before the input port
        return [*path, dest[1] + step_size, at_x]
    index = segment - 1
    if is_vertical(segment):
        # Down to the split, a step to the side, and on down
        step = [at_y, path[index] + step_size]
    else:
        # Along to the split, a step down, and on along
        step = [at_x, path[index] + step_size]
    return [*path[: index + 1], *step, *path[index + 1 :]]


def point_on_segment(
    source: Point, dest: Point, path: list[float], segment: int, point: Point
) -> Point:
    """The point of a segment closest to a point, like where the segment was clicked"""
    (start_x, start_y), (end_x, end_y) = corner_points(source, dest, path)[segment : segment + 2]
    return (
        min(max(point[0], min(start_x, end_x)), max(start_x, end_x)),
        min(max(point[1], min(start_y, end_y)), max(start_y, end_y)),
    )


def can_merge_segments(path: list[float], segment: int) -> bool:
    """Segments can be merged when the wire has more than one vertical segment"""
    return is_movable(path, segment) and len(path) >= 3


def merge_segments(path: list[float], segment: int) -> list[float]:
    """
    Merge segments, the opposite of split_segment: the segment and the one after it are
    removed (the one before it for the last movable segment), and the segments on each
    side are joined into one.
    """
    if not can_merge_segments(path, segment):
        raise ValueError(f"Segment {segment} can't be merged with its neighbors")
    index = segment - 1
    if index + 1 < len(path):
        return [*path[:index], *path[index + 2 :]]
    return path[: index - 1]


def is_inner_corner(path: list[float], corner: int) -> bool:
    """The corners between the segments, not the two ends of the wire"""
    return 1 <= corner <= len(path) + 1


def corner_at(
    source: Point, dest: Point, path: list[float], point: Point, radius: float
) -> int | None:
    """The inner corner within 'radius' of a point, like the mouse position, or None"""
    point_x, point_y = point
    points = corner_points(source, dest, path)
    for corner in range(1, len(points) - 1):
        corner_x, corner_y = points[corner]
        if math.hypot(point_x - corner_x, point_y - corner_y) <= radius:
            return corner
    return None


def nearest_corner(source: Point, dest: Point, path: list[float], point: Point) -> int:
    """The inner corner closest to a point"""
    points = corner_points(source, dest, path)
    return min(
        range(1, len(points) - 1),
        key=lambda corner: math.hypot(point[0] - points[corner][0], point[1] - points[corner][1]),
    )


def split_corner(segment: int, corner: int) -> int:
    """The number of a corner after split_segment(segment), which adds two corners"""
    return corner if corner <= segment else corner + 2


def merge_corner(path: list[float], segment: int, corner: int) -> int:
    """
    The number of a corner after merge_segments(path, segment). The three corners of the
    two removed segments become one.
    """
    index = segment - 1
    if index + 1 >= len(path):
        # The last movable segment is merged with the one before it
        index -= 1
    first = index + 1
    if corner <= first:
        return corner
    if corner <= first + 2:
        return first
    return corner - 2


def join_paths(
    parent_path: list[float], corner: int, corner_point: Point, branch_path: list[float]
) -> list[float]:
    """
    The path of a branch that starts at a corner of its parent wire, as one wire that
    runs from where the parent starts: the parent up to the corner, then the branch.
    'corner_point' is the position of the corner.
    """
    if not is_inner_corner(parent_path, corner):
        raise ValueError(f"Corner {corner} is not between two segments")
    prefix = parent_path[: corner - 1]
    if corner % 2 == 0:
        # After a vertical segment: across at the height of the corner to the branch
        return [*prefix, corner_point[1], *branch_path]
    # After a horizontal segment, which the branch continues
    return [*prefix, *branch_path]
