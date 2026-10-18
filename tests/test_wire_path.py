# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Pytest module to test the shape of wires in the GUI"""

from itertools import pairwise

import pytest

from digsim.app._wire_path import (
    SPLIT_STEP,
    X_OFFSET,
    arrival_offset,
    automatic_path,
    can_merge_segments,
    clicked_path,
    corner_at,
    corner_directions,
    corner_points,
    drawing_points,
    exits_vertically,
    handle_at,
    is_forwards,
    is_inner_corner,
    is_movable,
    is_valid_path,
    is_vertical,
    join_paths,
    merge_corner,
    merge_segments,
    move_segment,
    nearest_corner,
    nearest_segment,
    point_on_segment,
    segment_count,
    split_corner,
    split_segment,
    step_aside,
)


SOURCE_RECT = (0, 0, 80, 80)


def _segments(points):
    return list(pairwise(points))


def _check_shape(source, dest, path):
    """A wire starts and ends horizontally at its ports, and alternates directions"""
    points = corner_points(source, dest, path)
    assert points[0] == source
    assert points[-1] == dest
    segments = _segments(points)
    assert len(segments) == segment_count(path)
    for number, (start, end) in enumerate(segments):
        if is_vertical(number):
            assert start[0] == end[0], f"segment {number} is not vertical"
        else:
            assert start[1] == end[1], f"segment {number} is not horizontal"


@pytest.mark.parametrize(
    "source, dest, expected",
    [
        # Forwards: one vertical segment halfway between the ports
        ((100, 40), (300, 120), [(100, 40), (200, 40), (200, 120), (300, 120)]),
        # Backwards, to a port further up: above the source component
        (
            (100, 40),
            (20, -60),
            [(100, 40), (110, 40), (110, -10), (10, -10), (10, -60), (20, -60)],
        ),
        # Backwards, to a port further down: below the source component
        (
            (100, 40),
            (20, 300),
            [(100, 40), (110, 40), (110, 170), (10, 170), (10, 300), (20, 300)],
        ),
    ],
)
def test_automatic_path(source, dest, expected):
    """The automatic shape is the one the GUI has always drawn"""
    path = automatic_path(source, dest, SOURCE_RECT)
    assert is_valid_path(path)
    assert all(isinstance(value, int) for value in path)
    assert corner_points(source, dest, path) == expected
    _check_shape(source, dest, path)


def test_move_segments():
    """Vertical segments move sideways and inner horizontal segments up and down"""
    source, dest = (0, 0), (200, 100)
    path = [50, 30, 150]
    assert [is_movable(path, segment) for segment in range(5)] == [
        False,
        True,
        True,
        True,
        False,
    ]
    path = move_segment(path, 1, 70)
    path = move_segment(path, 2, 60)
    assert path == [70, 60, 150]
    assert corner_points(source, dest, path)[1:4] == [(70, 0), (70, 60), (150, 60)]
    _check_shape(source, dest, path)
    for segment in (0, 4):
        with pytest.raises(ValueError):
            move_segment(path, segment, 10)


def test_ports_move_inner_segments_stay():
    """When a component moves, only the segments at the ports follow it"""
    path = [50, 30, 150]
    before = corner_points((0, 0), (200, 100), path)
    after = corner_points((0, 20), (240, 120), path)
    # The inner corners, at the ends of the inner horizontal segment, stay
    assert after[2:4] == before[2:4]
    _check_shape((0, 20), (240, 120), path)


@pytest.mark.parametrize("segment", range(5))
def test_split_and_merge(segment):
    """Any segment can be split, which keeps the shape, and the split merged again"""
    source, dest = (0, 0), (200, 100)
    path = [50, 30, 150]
    at = corner_points(source, dest, path)[segment]
    split = split_segment(source, dest, path, segment, at)
    assert len(split) == len(path) + 2
    assert is_valid_path(split)
    _check_shape(source, dest, split)
    # Merging the new step gives a valid wire with two segments less
    new_segment = max(1, min(segment + 1, len(split)))
    assert can_merge_segments(split, new_segment)
    without = merge_segments(split, new_segment)
    assert len(without) == len(path)
    _check_shape(source, dest, without)


def test_split_corners():
    """Splitting a vertical segment makes a step to the side at the clicked height"""
    source, dest = (0, 0), (200, 100)
    path = split_segment(source, dest, [100], 1, (100, 40))
    assert path == [100, 40, 100 + SPLIT_STEP]
    assert corner_points(source, dest, path) == [
        (0, 0),
        (100, 0),
        (100, 40),
        (100 + SPLIT_STEP, 40),
        (100 + SPLIT_STEP, 100),
        (200, 100),
    ]


def test_merge_limits():
    """The last vertical segment, and the segments at the ports, can't be merged away"""
    path = [100]
    assert not any(can_merge_segments(path, segment) for segment in range(3))
    with pytest.raises(ValueError):
        merge_segments(path, 1)
    path = [50, 30, 150]
    assert [can_merge_segments(path, segment) for segment in range(5)] == [
        False,
        True,
        True,
        True,
        False,
    ]
    assert merge_segments(path, 1) == [150]
    assert merge_segments(path, 3) == [50]


def test_split_missing_segment():
    """Splitting a segment the wire doesn't have is an error"""
    with pytest.raises(ValueError):
        split_segment((0, 0), (100, 0), [50], 3, (0, 0))


def test_nearest_segment():
    """The segment closest to the mouse, also on a short segment between two others"""
    source, dest = (0, 0), (200, 100)
    path = [100, 40, 120]
    # (0, 0) (100, 0) (100, 40) (120, 40) (120, 100) (200, 100)
    assert nearest_segment(source, dest, path, (50, 3)) == 0
    assert nearest_segment(source, dest, path, (97, 20)) == 1
    assert nearest_segment(source, dest, path, (110, 42)) == 2
    assert nearest_segment(source, dest, path, (125, 70)) == 3
    assert nearest_segment(source, dest, path, (300, 90)) == 4


def test_clicked_path_from_output():
    """Drawn from the output port: across to each click, then up or down to it"""
    source, dest = (0, 0), (300, 100)
    path = clicked_path(source, dest, [(50, 40), (120, -30)])
    assert path == [50, 40, 120, -30, 300 - X_OFFSET]
    assert corner_points(source, dest, path) == [
        (0, 0),
        (50, 0),
        (50, 40),
        (120, 40),
        (120, -30),
        (300 - X_OFFSET, -30),
        (300 - X_OFFSET, 100),
        (300, 100),
    ]
    _check_shape(source, dest, path)
    # A last click past the input port: the last vertical segment just before the port
    assert clicked_path(source, dest, [(350, 40)])[-1] == 300 - X_OFFSET


def test_clicked_path_from_input():
    """Drawn from the input port, the wire runs the same way from that end"""
    source, dest = (0, 0), (300, 100)
    path = clicked_path(source, dest, [(250, 40), (120, -30)], from_source=False)
    points = corner_points(source, dest, path)
    # Backwards from the input port: across to (250, 100), up to (250, 40), across to
    # (120, 40), and up to (120, -30)
    assert points[::-1][:5] == [(300, 100), (250, 100), (250, 40), (120, 40), (120, -30)]
    assert path[0] == X_OFFSET
    _check_shape(source, dest, path)


@pytest.mark.parametrize("from_source", [True, False])
def test_drawing_matches_clicked_path(from_source):
    """While a wire is drawn, it looks like the wire that the clicks make"""
    source, dest = (0, 0), (300, 100)
    clicks = [(50, 40), (120, -30)]
    start, end = (source, dest) if from_source else (dest, source)
    drawn = drawing_points(start, clicks)
    points = corner_points(source, dest, clicked_path(source, dest, clicks, from_source))
    if not from_source:
        points = points[::-1]
    # The finished wire starts like the drawn one, then continues to the other port
    assert points[: len(drawn)] == drawn
    assert points[-1] == end


@pytest.mark.parametrize("clicks", [[], [(50, 40)], [(50, 40), (350, -30)]])
@pytest.mark.parametrize("from_source", [True, False])
def test_finished_like_drawn(clicks, from_source):
    """
    The wire keeps the shape it was drawn with when the port is clicked, except that it
    reaches that port horizontally, from just before it
    """
    source, dest = (0, 0), (300, 100)
    start, end = (source, dest) if from_source else (dest, source)
    drawn = drawing_points(start, [*clicks, end])
    points = corner_points(source, dest, clicked_path(source, dest, clicks, from_source))
    if not from_source:
        points = points[::-1]
    step = -X_OFFSET if from_source else X_OFFSET
    # The drawn wire runs across to the port and then up or down to it
    assert points[:-3] == drawn[:-2]
    assert points[-3:] == [
        (end[0] + step, drawn[-3][1]),
        (end[0] + step, end[1]),
        end,
    ]
    assert is_forwards(source, dest)
    assert not is_forwards(dest, source)


def test_handle_at():
    """Segments are dragged by the handle in their middle, not the ones at the ports"""
    source, dest = (0, 0), (200, 100)
    path = [100, 40, 120]
    # (0, 0) (100, 0) (100, 40) (120, 40) (120, 100) (200, 100)
    assert handle_at(source, dest, path, (100, 20), 5) == 1
    assert handle_at(source, dest, path, (113, 37), 5) == 2
    assert handle_at(source, dest, path, (121, 74), 5) == 3
    # Beside the handle, and on the segments at the ports
    assert handle_at(source, dest, path, (100, 30), 5) is None
    assert handle_at(source, dest, path, (50, 0), 5) is None
    assert handle_at(source, dest, path, (160, 100), 5) is None
    # A segment without length has no handle: the vertical one at x = 100 here
    assert handle_at(source, dest, [100, 0, 150], (100, 0), 5) is None
    assert handle_at(source, dest, [100, 0, 150], (125, 0), 5) == 2


def test_corner_at():
    """A wire can be started at its inner corners, not at the ports"""
    source, dest = (0, 0), (200, 100)
    path = [100, 40, 120]
    # (0, 0) (100, 0) (100, 40) (120, 40) (120, 100) (200, 100)
    assert corner_at(source, dest, path, (102, 1), 5) == 1
    assert corner_at(source, dest, path, (120, 98), 5) == 4
    assert corner_at(source, dest, path, (110, 40), 5) is None
    assert corner_at(source, dest, path, (0, 0), 5) is None
    assert corner_at(source, dest, path, (200, 100), 5) is None
    assert nearest_corner(source, dest, path, (0, 0)) == 1
    assert nearest_corner(source, dest, path, (300, 100)) == 4
    assert [is_inner_corner(path, corner) for corner in range(6)] == [
        False,
        True,
        True,
        True,
        True,
        False,
    ]


@pytest.mark.parametrize("segment", range(5))
def test_split_corner(segment):
    """After a split, the corners away from the split segment are where they were"""
    source, dest = (0, 0), (200, 100)
    path = [50, 30, 150]
    before = corner_points(source, dest, path)
    at = before[segment]
    after = corner_points(source, dest, split_segment(source, dest, path, segment, at))
    new_corners = [split_corner(segment, corner) for corner in range(len(before))]
    assert new_corners == sorted(new_corners)
    assert new_corners[-1] == len(after) - 1
    for corner, new_corner in enumerate(new_corners):
        # The step moves one end of the split segment
        if corner not in (segment, segment + 1):
            assert after[new_corner] == before[corner]


@pytest.mark.parametrize("segment", range(1, 4))
def test_merge_corner(segment):
    """After a merge, the corners away from the merged segments are where they were"""
    source, dest = (0, 0), (200, 100)
    path = [50, 30, 150, 60, 170]
    before = corner_points(source, dest, path)
    after = corner_points(source, dest, merge_segments(path, segment))
    new_corners = [merge_corner(path, segment, corner) for corner in range(len(before))]
    # Three corners become one, the others are kept in order
    assert sorted(set(new_corners)) == list(range(len(after)))
    assert new_corners[0] == 0
    assert new_corners[-1] == len(after) - 1
    for corner, new_corner in enumerate(new_corners):
        if new_corners.count(new_corner) == 1:
            assert after[new_corner] == before[corner]


@pytest.mark.parametrize("corner", range(1, 5))
def test_join_paths(corner):
    """A branch joined with its parent runs from the parent's start to the branch's end"""
    source, dest = (0, 0), (200, 100)
    parent = [50, 30, 150]
    points = corner_points(source, dest, parent)
    branch_dest = (300, -50)
    branch = automatic_path(points[corner], branch_dest, (*points[corner], 0, 0))
    joined = join_paths(parent, corner, points[corner], branch)
    assert is_valid_path(joined)
    _check_shape(source, branch_dest, joined)
    joined_points = corner_points(source, branch_dest, joined)
    # The same wire: the parent's corners before the branch, then the branch's corners
    assert joined_points[:corner] == points[:corner]
    branch_points = corner_points(points[corner], branch_dest, branch)
    assert joined_points[-len(branch_points) + 1 :] == branch_points[1:]
    with pytest.raises(ValueError):
        join_paths(parent, 0, source, branch)


@pytest.mark.parametrize("segment", range(5))
def test_add_joint(segment):
    """A joint keeps the shape of the wire, and adds a corner where it was put"""
    source, dest = (0, 0), (200, 100)
    path = [50, 30, 150]
    before = corner_points(source, dest, path)
    (x1, y1), (x2, y2) = before[segment : segment + 2]
    at = ((x1 + x2) / 2, (y1 + y2) / 2)
    joined = split_segment(source, dest, path, segment, at, step_size=0)
    assert is_valid_path(joined)
    after = corner_points(source, dest, joined)
    # The same line, with the joint twice (the two ends of a segment without length)
    assert after == [*before[: segment + 1], at, at, *before[segment + 1 :]]
    assert corner_at(source, dest, joined, at, 5) == segment + 1
    # The corners after the joint are where they were
    for corner, point in enumerate(before):
        assert after[split_corner(segment, corner)] == point


def test_point_on_segment():
    """A click beside a segment is moved onto it, also past its end"""
    source, dest = (0, 0), (200, 100)
    path = [50, 30, 150]
    # (0, 0) (50, 0) (50, 30) (150, 30) (150, 100) (200, 100)
    assert point_on_segment(source, dest, path, 0, (20, 6)) == (20, 0)
    assert point_on_segment(source, dest, path, 1, (55, 40)) == (50, 30)
    assert point_on_segment(source, dest, path, 2, (100, 27)) == (100, 30)


def test_branch_drawn_to_wire():
    """A wire drawn from an input port to another wire reaches it without a step"""
    joint, dest = (100, 0), (300, 100)
    path = clicked_path(joint, dest, [(200, 50)], from_source=False, source_offset=0)
    points = corner_points(joint, dest, path)
    assert points[:3] == [joint, joint, (100, 50)]


def test_automatic_path_whole_numbers():
    """Halfway between ports an odd distance apart is a whole number too"""
    assert automatic_path((0, 0), (101, 50), SOURCE_RECT) == [50]
    assert automatic_path((100.0, 41.0), (20.0, 300.0), SOURCE_RECT) == [110, 170, 10]


def test_corner_directions():
    """A joint has the two directions of its straight line, a corner one of each"""
    source, dest = (0, 0), (200, 100)
    path = [50, 0, 100, 60, 100, 100, 150]
    # (0, 0) (50, 0) (50, 0) (100, 0) (100, 60) (100, 60) (100, 100) (150, 100) ...
    points = corner_points(source, dest, path)
    assert corner_directions(points, 1) == {"left", "right"}
    assert corner_directions(points, 2) == {"left", "right"}
    assert corner_directions(points, 3) == {"left", "down"}
    assert corner_directions(points, 4) == {"up", "down"}


def test_branch_leaves_across():
    """A branch leaves a joint on a horizontal wire up or down, and a vertical one across"""
    horizontal, vertical = {"left", "right"}, {"up", "down"}
    assert exits_vertically(horizontal, (50, 0), (200, 100))
    assert not exits_vertically(vertical, (50, 0), (200, 100))
    # At a corner, across when the wire doesn't run that way
    assert not exits_vertically({"left", "down"}, (100, 0), (200, 100))
    assert exits_vertically({"right", "down"}, (100, 0), (200, 100))


def test_branch_reaches_across():
    """A wire reaches a joint on a vertical wire from the side, with a step"""
    horizontal, vertical = {"left", "right"}, {"up", "down"}
    assert arrival_offset(horizontal, (100, 50), (300, 200)) == 0
    assert arrival_offset(vertical, (100, 50), (300, 200)) == X_OFFSET
    assert arrival_offset(vertical, (100, 50), (20, 200)) == -X_OFFSET


@pytest.mark.parametrize("clicks", [[], [(120, 60)], [(120, 60), (180, -40)]])
def test_vertical_first_like_drawn(clicks):
    """A wire drawn up or down first from a joint keeps exactly the drawn shape"""
    joint, dest = (100, 0), (300, 100)
    drawn = drawing_points(joint, [*clicks, dest], vertical_first=True)
    path = clicked_path(joint, dest, clicks, vertical_first=True)
    assert is_valid_path(path)
    points = corner_points(joint, dest, path)
    # Without the segments of no length at the start
    assert [p for i, p in enumerate(points) if i == 0 or p != points[i - 1]] == [
        p for i, p in enumerate(drawn) if i == 0 or p != drawn[i - 1]
    ]
    # Up or down from the joint
    assert points[1] == joint
    assert points[2][0] == joint[0]


def test_step_aside():
    """A branch to a port at the height of the joint steps down instead of along the wire"""
    joint, port = (100, 50), (20, 50)
    horizontal = {"left", "right"}
    path = step_aside([100], joint, port, horizontal)
    assert path == [100, 50 + SPLIT_STEP, 20 - X_OFFSET]
    points = corner_points(joint, port, path)
    assert points[2] == (100, 50 + SPLIT_STEP)
    # Up or down, or away from the wire: no step
    assert step_aside([100], joint, (20, 120), horizontal) == [100]
    assert step_aside([100], joint, port, {"up", "down"}) == [100]
