# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""
The wires drawn in the GUI, and the lines that they make
(kept free from Qt imports so that it can be tested without a display)

Every connection of the circuit, (output port, input port) (see Wire), is a wire in the
GUI. A drawn wire has a path (see digsim.app._wire_path), and is known by its two ports:
a connection, or two ports of the same kind. It starts at its first port, or at a corner
of another drawn wire from the same port (a branch, see digsim.app._wire_tree). It ends
at its second port, or at a corner of a drawn wire from another port: it joins the line
of that wire there.

The drawn wires make lines: wires that start or end on each other, or at the same port,
are on the same line. Each output port of a line drives each input port of it, like the
outputs and inputs on one wire of a real circuit. A connection that isn't drawn is
implied by the line that its ports are on. A joined wire is known by a port of its line,
that it doesn't reach itself.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from functools import partial
from itertools import pairwise
from typing import TYPE_CHECKING, NamedTuple

from digsim.app import _line_graph, _wire_tree
from digsim.app._wire_key import Wire, drawn_key, is_connection, port_key, wire_key
from digsim.app._wire_path import (
    X_OFFSET,
    Point,
    Rect,
    arrival_offset,
    automatic_path,
    clicked_path,
    corner_directions,
    corner_points,
    exits_vertically,
    follow_joint,
    is_forwards,
    is_inner_corner,
    is_movable,
    is_valid_path,
    is_vertical,
    joint_bounds,
    move_segment,
    nearest_corner,
    point_on_segment,
    split_at_port,
    split_corner,
    split_segment,
    step_aside,
)
from digsim.circuit.components.atoms import VALUE_TYPE, Port, PortConnectionError, resolve
from digsim.storage_model import GuiWireDataClass, LineDataClass


if TYPE_CHECKING:
    from collections.abc import Callable

    from digsim.circuit.components.atoms import Component


# A node of the lines: ("port", port) or ("wire", wire)
Node = tuple[str, object]

# Where a new wire ends on a drawn wire: a corner, or a segment and the point of a new joint
At = int | tuple[int, Point]

# A segment of a line's graph: the number of the line, and its two nodes
GraphSegment = tuple[int, frozenset[str]]


class PointMove(NamedTuple):
    """
    How a point where wires meet moves: a segment of a wire moves across, a joint (a
    segment without length) or a segment at a corner, between bounds. A segment at a port
    is split next to the port first ('split', see _wire_path.split_at_port()).
    """

    wire: Wire
    segment: int
    bounds: tuple[float, float]
    split: bool = False


class Line(NamedTuple):
    """The drawn wires of a line, and its output and input ports"""

    wires: list[Wire]
    outputs: list[Port]
    inputs: list[Port]


class Lines:
    """The lines of the drawn wires: the ports and wires that are connected"""

    def __init__(self, edges: Iterable[tuple[Wire, Node, Node]]) -> None:
        self._parent: dict[Node, Node] = {}
        for wire, start, end in edges:
            self._union(("wire", wire), start)
            self._union(("wire", wire), end)

    def find(self, node: Node) -> Node:
        """The node that stands for the line of a node"""
        root = node
        while self._parent.get(root, root) != root:
            root = self._parent[root]
        while node != root:
            self._parent[node], node = root, self._parent[node]
        return root

    def _union(self, first: Node, second: Node) -> None:
        first_root, second_root = self.find(first), self.find(second)
        if first_root != second_root:
            self._parent[first_root] = second_root

    def same(self, first: Node, second: Node) -> bool:
        """Are two nodes on the same line"""
        return self.find(first) == self.find(second)


class WireDrawing:
    """
    The drawn wires and their paths. A drawn wire keeps its path when components move:
    only the segments at the ports follow them. The GUI gives the connections, the ports
    and their positions (connections(), ports(), port_pos() and port_rect()).
    """

    def __init__(self) -> None:
        self._paths: dict[Wire, list[float]] = {}
        # Branch: the wire it starts on and the corner it starts at
        self._branches: dict[Wire, tuple[Wire, int]] = {}
        # Joined wire: the wire it ends on and the corner it ends at
        self._joins: dict[Wire, tuple[Wire, int]] = {}
        # The connections that are not drawn
        self._implied: set[Wire] = set()
        # Where joined wires end while wires are removed, their joint doesn't move
        self._fixed_ends: dict[Wire, Point] = {}

    def connections(self) -> list[Wire]:
        """The connections of the circuit, (output port, input port)"""
        raise NotImplementedError

    def ports(self) -> list[Port]:
        """All ports of the components"""
        raise NotImplementedError

    def port_pos(self, port: Port) -> Point:
        """The position of a port"""
        raise NotImplementedError

    def port_rect(self, port: Port) -> Rect:
        """The rectangle of a port's component, that a wire runs around"""
        raise NotImplementedError

    def _push_undo(self) -> None:
        """Called before a change that is an undo step of its own"""

    def _changed(self) -> None:
        """Called after the path of a wire changed"""

    def clear(self) -> None:
        """Forget all wires"""
        self._paths = {}
        self._branches = {}
        self._joins = {}
        self._implied = set()

    # The wires and lines

    def drawn(self) -> list[Wire]:
        """The drawn wires: the connections that are not implied, and the other wires"""
        connections = self.connections()
        known = set(connections)
        return [wire for wire in connections if wire not in self._implied] + [
            wire for wire in self._paths if wire not in known
        ]

    def is_implied(self, wire: Wire) -> bool:
        """Is a connection implied by its line, not drawn"""
        return wire in self._implied

    def branch(self, wire: Wire) -> tuple[Wire, int] | None:
        """The wire that a wire starts on and the corner it starts at, None at the port"""
        return self._branches.get(wire)

    def join(self, wire: Wire) -> tuple[Wire, int] | None:
        """The wire that a joined wire ends on and the corner it ends at, None at the port"""
        return self._joins.get(wire)

    def _start_node(self, wire: Wire) -> Node:
        branch = self._branches.get(wire)
        return ("port", wire[0]) if branch is None else ("wire", branch[0])

    def _end_node(self, wire: Wire) -> Node:
        join = self._joins.get(wire)
        return ("port", wire[1]) if join is None else ("wire", join[0])

    def lines(self, wires: Iterable[Wire] | None = None) -> Lines:
        """The lines of the drawn wires (or of some of them)"""
        return Lines(
            (wire, self._start_node(wire), self._end_node(wire))
            for wire in (self.drawn() if wires is None else wires)
        )

    def line(self, node: Node) -> Line:
        """The line of a port, ("port", port), or of a drawn wire, ("wire", wire)"""
        drawn = self.drawn()
        lines = self.lines(drawn)
        root = lines.find(node)
        wires = [wire for wire in drawn if lines.find(("wire", wire)) == root]
        outputs: list[Port] = []
        inputs: list[Port] = []
        for wire in wires:
            for end in (self._start_node(wire), self._end_node(wire)):
                port = end[1]
                if isinstance(port, Port):
                    group = outputs if port.is_output() else inputs
                    if port not in group:
                        group.append(port)
        if node[0] == "port" and not wires:
            port = node[1]
            assert isinstance(port, Port)
            return Line([], [port] if port.is_output() else [], [port] if port.is_input() else [])
        return Line(wires, outputs, inputs)

    def drawing_order(self, wires: list[Wire] | None = None) -> list[Wire]:
        """The drawn wires (or some of them), each after the wires it starts or ends on"""
        pending = self.drawn() if wires is None else list(wires)
        ordered: list[Wire] = []
        done: set[Wire] = set()
        while pending:
            left = []
            for wire in pending:
                anchors = [self._branches.get(wire), self._joins.get(wire)]
                if all(anchor is None or anchor[0] in done for anchor in anchors):
                    ordered.append(wire)
                    done.add(wire)
                else:
                    left.append(wire)
            if len(left) == len(pending):
                raise ValueError(f"Wires that start or end on each other: {left}")
            pending = left
        return ordered

    def line_outputs(self) -> dict[Wire, list[Port]]:
        """The output ports of the line of each drawn wire"""
        drawn = self.drawn()
        lines = self.lines(drawn)
        outputs: dict[Node, list[Port]] = {}
        for wire in drawn:
            for end in (self._start_node(wire), self._end_node(wire)):
                port = end[1]
                if isinstance(port, Port) and port.is_output():
                    group = outputs.setdefault(lines.find(end), [])
                    if port not in group:
                        group.append(port)
        return {wire: outputs.get(lines.find(("wire", wire)), []) for wire in drawn}

    @staticmethod
    def value(outputs: list[Port]) -> VALUE_TYPE:
        """
        The value of a line with these output ports: what they drive together, "X" if
        they drive different values, "Z" if none drives it (see resolve)
        """
        return resolve([port.value for port in outputs])

    def line_value(self, wire: Wire) -> VALUE_TYPE:
        """The value of the line of a drawn wire, see value()"""
        return self.value(self.line(("wire", wire)).outputs)

    def line_wires(self, wire: Wire) -> list[Wire]:
        """The drawn wires of the line of a drawn wire"""
        return self.line(("wire", wire)).wires

    def is_connected(self, wire: Wire, lines: Lines | None = None) -> bool:
        """Are the ports of a connection on the same line"""
        if lines is None:
            lines = self.lines()
        return lines.same(("port", wire[0]), ("port", wire[1]))

    # The shape of a drawn wire

    def start_point(self, wire: Wire) -> Point:
        """Where a wire starts: at the output port, or at a corner of another wire"""
        branch = self._branches.get(wire)
        if branch is None:
            return self.port_pos(wire[0])
        parent, corner = branch
        return self.corner_points(parent)[corner]

    def end_point(self, wire: Wire) -> Point:
        """Where a wire ends: at the input port, or at a corner of another wire"""
        if wire in self._fixed_ends:
            return self._fixed_ends[wire]
        joint = self._joins.get(wire)
        if joint is None:
            return self.port_pos(wire[1])
        host, corner = joint
        return self.corner_points(host)[corner]

    def taken_directions(self, wire: Wire, corner: int) -> set[str]:
        """The directions that a wire runs in from one of its corners"""
        return corner_directions(self.corner_points(wire), corner)

    def corner_points(self, wire: Wire) -> list[Point]:
        """The points of a wire, from where it starts to where it ends"""
        return corner_points(self.start_point(wire), self.end_point(wire), self.path(wire))

    def automatic_path(self, wire: Wire) -> list[float]:
        """The automatic path of a wire, for the current component positions"""
        src_port, dst_port = wire
        if wire in self._joins:
            start, end = self.start_point(wire), self.end_point(wire)
            if wire in self._branches or is_forwards(start, end):
                # Across, and up or down to the joint (or across, see arrival_offset)
                taken = self.taken_directions(*self._joins[wire])
                return [end[0] + arrival_offset(taken, end, start)]
        elif wire in self._branches:
            # From the corner where the branch starts, with nothing to run around, and
            # not along the wire it starts on
            start, dest = self.start_point(wire), self.port_pos(dst_port)
            taken = self.taken_directions(*self._branches[wire])
            if exits_vertically(taken, start, dest):
                if start[0] < dest[0]:
                    return step_aside([start[0]], start, dest, taken)
                return [start[0], math.floor((start[1] + dest[1]) / 2), dest[0] - X_OFFSET]
            if start[0] < dest[0]:
                return [math.floor((start[0] + dest[0]) / 2)]
            return [dest[0] - X_OFFSET]
        elif src_port.is_output() == dst_port.is_output():
            # Between ports of the same kind: beside them, left of input ports and right
            # of output ports
            start, end = self.port_pos(src_port), self.port_pos(dst_port)
            if src_port.is_output():
                return [max(start[0], end[0]) + X_OFFSET]
            return [min(start[0], end[0]) - X_OFFSET]
        return automatic_path(
            self.port_pos(src_port), self.end_point(wire), self.port_rect(src_port)
        )

    def path(self, wire: Wire) -> list[float]:
        """The path of a drawn wire, a wire without a path gets the automatic path"""
        if wire in self._implied:
            raise ValueError(f"{wire_key(wire)} is not drawn")
        if wire not in self._paths:
            self._paths[wire] = self.automatic_path(wire)
        return self._paths[wire]

    def _new_path(self, wire: Wire, clicks: Sequence[Point], from_source: bool) -> list[float]:
        """
        The path of a new wire, through the positions clicked while it was drawn, from
        where it starts, or from where it ends (not 'from_source')
        """
        start, end = self.start_point(wire), self.end_point(wire)
        clicks = list(clicks)
        branch, join = self._branches.get(wire), self._joins.get(wire)
        if join is not None:
            if not clicks and branch is None:
                return self.automatic_path(wire)
            if from_source:
                # Up or down to the joint, or across (see arrival_offset)
                taken = self.taken_directions(*join)
                path = [value for click in clicks for value in click]
                path.append(end[0] + arrival_offset(taken, end, clicks[-1] if clicks else start))
                return path
            return clicked_path(start, end, clicks, from_source=False)
        if branch is not None:
            # Like it was drawn, a wire from a corner has no component to run around. It
            # leaves or reaches the corner across the other wire, not along it.
            taken = self.taken_directions(*branch)
            if from_source:
                toward = clicks[0] if clicks else end
                vertical_first = exits_vertically(taken, start, toward)
                path = clicked_path(start, end, clicks, vertical_first=vertical_first)
                if not clicks and not vertical_first and path[0] == start[0]:
                    # The port is just beside the corner: up or down halfway to it, not
                    # from the corner along the other wire
                    path = [math.floor((start[0] + end[0]) / 2)]
            else:
                offset = arrival_offset(taken, start, clicks[-1] if clicks else end)
                path = clicked_path(start, end, clicks, False, offset)
            return step_aside(path, start, end, taken)
        if wire[0].is_output() == wire[1].is_output():
            if not clicks:
                return self.automatic_path(wire)
            # Like it was drawn, and to the side of the port where it ends
            path = clicked_path(start, end, clicks)
            path[-1] = end[0] + (X_OFFSET if wire[1].is_output() else -X_OFFSET)
            return path
        if clicks or is_forwards(start, end):
            return clicked_path(start, end, clicks, from_source)
        return self.automatic_path(wire)

    def set_path(
        self,
        wire: Wire,
        path: list[float],
        corner_map: Callable[[int], int] | None = None,
        undo: bool = True,
    ) -> None:
        """
        Change the path of a wire (an undo step, unless it is part of another one). The
        branches that start on it, and the joined wires that end on it, keep their
        corner, moved by 'corner_map' when the change adds or removes corners, or the
        corner closest to where they were.
        """
        if not is_valid_path(path):
            raise ValueError(f"Invalid wire path {path}")
        if self._paths.get(wire) == path:
            return
        if undo:
            self._push_undo()
        children = _wire_tree.children(self._branches, wire)
        joined = [other for other, (host, _) in self._joins.items() if host == wire]
        old_points = self.corner_points(wire) if children or joined else []
        old_length = len(self._paths.get(wire, path))
        self._paths[wire] = list(path)

        def new_corner(corner: int) -> int:
            if corner_map is not None:
                return corner_map(corner)
            if len(path) != old_length:
                start, end = self.start_point(wire), self.end_point(wire)
                return nearest_corner(start, end, path, old_points[corner])
            return corner

        for child in children:
            self._branches[child] = (wire, new_corner(self._branches[child][1]))
        for other in joined:
            self._joins[other] = (wire, new_corner(self._joins[other][1]))
        self._changed()

    def move_paths(self, paths: dict[Wire, list[float]], dx: int, dy: int) -> None:
        """
        Give wires their paths moved by (dx, dy), while components that they run between
        are moved together (part of the move's undo step)
        """
        for wire, path in paths.items():
            self._paths[wire] = [
                value + (dy if index % 2 else dx) for index, value in enumerate(path)
            ]

    def moving_wires(self, moving: set[Component]) -> list[Wire]:
        """
        The wires that move with components that are moved together: between them, and the
        joined wires from them to a wire that moves too
        """
        drawn = self.drawn()
        wires = [
            wire
            for wire in drawn
            if wire not in self._joins
            and wire[0].parent() in moving
            and wire[1].parent() in moving
        ]
        found = set(wires)
        added = True
        while added:
            added = False
            for wire in drawn:
                joint = self._joins.get(wire)
                if (
                    joint is not None
                    and wire not in found
                    and wire[0].parent() in moving
                    and joint[0] in found
                ):
                    wires.append(wire)
                    found.add(wire)
                    added = True
        return wires

    def anchor_point(self, wire: Wire, at: At) -> Point:
        """Where a new wire starts on a wire: a corner, or a point on a segment"""
        if isinstance(at, int):
            return self.corner_points(wire)[at]
        segment, point = at
        return point_on_segment(
            self.start_point(wire), self.end_point(wire), self.path(wire), segment, point
        )

    def anchor_directions(self, wire: Wire, at: At) -> set[str]:
        """The directions that a wire runs in from where a new wire starts on it"""
        if isinstance(at, int):
            return self.taken_directions(wire, at)
        # Along the segment, both ways
        return {"up", "down"} if is_vertical(at[0]) else {"left", "right"}

    def joint_bounds(self, wire: Wire, segment: int) -> tuple[float, float] | None:
        """How far a joint of a wire can move along it, see _wire_path.joint_bounds()"""
        return joint_bounds(self.start_point(wire), self.end_point(wire), self.path(wire), segment)

    def joint_followers(
        self, wire: Wire, segment: int, position: float
    ) -> dict[Wire, list[float]]:
        """
        The new paths of the wires that start or end at a joint of a wire that moves
        along it to 'position': a wire that leaves or reaches the joint across the wire
        keeps doing so. On a vertical run they do that by themselves.
        """
        old = self.path(wire)[segment - 1]
        followers: dict[Wire, list[float]] = {}
        for other in dict.fromkeys([*self._branches, *self._joins]):
            branch, join = self._branches.get(other), self._joins.get(other)
            path = follow_joint(
                segment,
                old,
                position,
                self.path(other),
                branch[1] if branch is not None and branch[0] == wire else None,
                join[1] if join is not None and join[0] == wire else None,
            )
            if path is not None:
                followers[other] = path
        return followers

    def point_move(self, point: Point) -> PointMove | None:
        """
        How a point where wires meet, or a joint, can move along the straight line through
        it: a joint of a wire on a straight run moves along it, and at a corner of a wire,
        where other wires go on straight, the corner's segment across moves with it.
        Between the next corners or points on each side. None if it can't move.
        """
        drawn = self.drawn()
        for wire in drawn:
            points = self.corner_points(wire)
            for segment in range(1, len(self.path(wire)) + 1):
                if points[segment] == point:
                    bounds = self.joint_bounds(wire, segment)
                    if bounds is not None:
                        return PointMove(wire, segment, bounds)
        # The segments of the line at the point
        lines = self.lines(drawn)
        legs: list[tuple[Wire, int, Point, Point]] = []
        for wire in drawn:
            points = self.corner_points(wire)
            for segment, (start, end) in enumerate(pairwise(points)):
                if start != end and _line_graph.on_segment(start, end, point):
                    legs.append((wire, segment, start, end))
        if not legs:
            return None
        # The point is of the line that goes the most ways there (where a wire of another
        # line runs through a dot)
        by_line: dict[Node, list[tuple[Wire, int, Point, Point]]] = {}
        for leg in legs:
            by_line.setdefault(lines.find(("wire", leg[0])), []).append(leg)

        legs = max(
            by_line.values(),
            key=lambda line_legs: len(
                _line_graph.ways(point, [(start, end) for _, _, start, end in line_legs])
            ),
        )
        for wire, segment, start, end in legs:
            at_port = self._is_port_segment(wire, segment)
            if point not in (start, end) or not (is_movable(self.path(wire), segment) or at_port):
                continue
            if at_port and point == (start if segment == 0 else end):
                # The port itself doesn't move
                continue
            # The segment moves across: along the other axis, the line must go both ways
            axis = 0 if is_vertical(segment) else 1
            reach: dict[int, float] = {}
            for _, _, first, second in legs:
                if first[1 - axis] != second[1 - axis] or first[1 - axis] != point[1 - axis]:
                    continue
                for end_point in (first, second):
                    way = (end_point[axis] > point[axis]) - (end_point[axis] < point[axis])
                    if way:
                        distance = abs(end_point[axis] - point[axis])
                        reach[way] = min(reach.get(way, distance), distance)
            if 1 in reach and -1 in reach and reach[1] + reach[-1] >= 2:
                bounds = (point[axis] - reach[-1] + 1, point[axis] + reach[1] - 1)
                return PointMove(wire, segment, bounds, at_port)
        return None

    def _is_port_segment(self, wire: Wire, segment: int) -> bool:
        """Is a segment of a wire attached to a port: the first or the last, at the port"""
        return (segment == 0 and wire not in self._branches) or (
            segment == len(self.path(wire)) + 1 and wire not in self._joins
        )

    def move_point(self, move: PointMove, position: float) -> None:
        """
        Move a point where wires meet, or a joint (see point_move()), an undo step. The
        wires that start or end there follow it.
        """
        wire, segment, (low, high), split = move
        position = min(max(position, low), high)
        if not split and position == self.path(wire)[segment - 1]:
            return
        self._push_undo()
        if split:
            # Next to the port, the part away from it moves
            path, moving = split_at_port(
                self.start_point(wire), self.end_point(wire), self.path(wire), segment
            )
            self._paths[wire] = path
            for other, anchors in self._anchored(wire):
                anchors[other] = (wire, split_corner(segment, anchors[other][1]))
            segment = moving
        followers = self.joint_followers(wire, segment, position)
        self._paths[wire] = move_segment(self.path(wire), segment, position)
        self._paths.update(followers)
        self._changed()

    def move_joint(self, wire: Wire, segment: int, position: float) -> None:
        """
        Move a joint of a wire along it, between the corners of its straight run (an
        undo step). The wires that start or end there follow it.
        """
        bounds = self.joint_bounds(wire, segment)
        if bounds is None:
            raise ValueError(f"Segment {segment} of {wire_key(wire)} is not a joint")
        position = min(max(position, bounds[0]), bounds[1])
        if position == self.path(wire)[segment - 1]:
            return
        self._push_undo()
        followers = self.joint_followers(wire, segment, position)
        self._paths[wire] = move_segment(self.path(wire), segment, position)
        self._paths.update(followers)
        self._changed()

    def add_joint(self, wire: Wire, segment: int, point: Point, undo: bool = True) -> int:
        """
        Add a joint to a segment of a wire, at the point of the segment closest to 'point':
        a corner, where a wire can start or end, that keeps the wire's shape. Returns the
        corner.
        """
        start, end = self.start_point(wire), self.end_point(wire)
        path = self.path(wire)
        at = point_on_segment(start, end, path, segment, point)
        new_path = split_segment(start, end, path, segment, at, step_size=0)
        self.set_path(wire, new_path, partial(split_corner, segment), undo)
        return segment + 1

    # The wire trees, see digsim.app._wire_tree

    def tree(self, wire: Wire) -> list[Wire]:
        """All drawn wires from the same output port, that start on each other"""
        return _wire_tree.tree(self._branches, wire)

    def route(self, wire: Wire) -> dict[Wire, int | None]:
        """The wires on the way from the output port, see _wire_tree.route()"""
        return _wire_tree.route(self._branches, wire)

    # New wires

    def _check_new(self, start: Node, end: Node, what: str) -> None:
        """A new wire must connect two lines (a port without wires is a line of its own)"""
        if self.lines().same(start, end):
            raise PortConnectionError(f"{what} are on the same line already")

    def _corner(self, wire: Wire, at: At) -> int:
        """The corner where a new wire starts or ends, a new joint on a segment"""
        if isinstance(at, int):
            return at
        return self.add_joint(wire, *at, undo=False)

    def _add(
        self,
        wire: Wire,
        clicks: Sequence[Point],
        from_source: bool,
        branch: tuple[Wire, int] | None = None,
        join: tuple[Wire, int] | None = None,
    ) -> None:
        self._implied.discard(wire)
        # Nothing starts or ends on a new wire, an earlier wire with the same ports is gone
        for child in _wire_tree.children(self._branches, wire):
            del self._branches[child]
        for other in [other for other, (host, _) in self._joins.items() if host == wire]:
            del self._joins[other]
        self._branches.pop(wire, None)
        self._joins.pop(wire, None)
        self._paths.pop(wire, None)
        if branch is not None:
            self._branches[wire] = branch
        if join is not None:
            self._joins[wire] = join
        self._paths[wire] = self._new_path(wire, clicks, from_source)

    @staticmethod
    def _connect(wire: Wire) -> None:
        """
        Connect the ports of a new drawn wire, if it goes from an output port to an input
        port (other wires connect ports through their line, see _complete())
        """
        src_port, dst_port = wire
        if src_port.width != dst_port.width:
            raise PortConnectionError("Cannot connect ports with different widths")
        if src_port.is_output() and dst_port.is_input():
            src_port.wire = dst_port

    def _complete(self, port: Port) -> None:
        """Connect each output port of the line of a port to each of its input ports"""
        line = self.line(("port", port))
        for src_port in line.outputs:
            for dst_port in line.inputs:
                if dst_port not in src_port.wired_ports:
                    src_port.wire = dst_port
                    self._implied.add((src_port, dst_port))

    def connect_ports(
        self,
        src_port: Port,
        dst_port: Port,
        clicks: Sequence[Point] = (),
        from_source: bool = True,
    ) -> None:
        """
        A wire drawn between two ports: from an output port to an input port, or from the
        input port (not 'from_source'), or from a port to another port of the same kind.
        Their lines become one. Raises PortConnectionError, and changes nothing, if they
        can't be connected.
        """
        if src_port is dst_port:
            raise PortConnectionError("A wire can't end at the port where it starts")
        self._check_new(
            ("port", src_port),
            ("port", dst_port),
            f"{port_key(src_port)} and {port_key(dst_port)}",
        )
        self._connect((src_port, dst_port))
        self._add((src_port, dst_port), clicks, from_source)
        self._complete(src_port)

    def connect_branch(
        self,
        line_wire: Wire,
        at: At,
        dst_port: Port,
        clicks: Sequence[Point] = (),
        from_source: bool = True,
    ) -> None:
        """
        A wire drawn from a corner of a drawn wire ('at', or a new joint on a segment) to
        an input port, or from the input port to the corner (not 'from_source'): a branch
        of the drawn wire. The input port joins its line.
        """
        self._check_new(
            ("wire", line_wire), ("port", dst_port), f"The wire and {port_key(dst_port)}"
        )
        src_port = line_wire[0]
        self._connect((src_port, dst_port))
        corner = self._corner(line_wire, at)
        self._add((src_port, dst_port), clicks, from_source, branch=(line_wire, corner))
        self._complete(dst_port)

    def connect_join(
        self,
        src_port: Port,
        line_wire: Wire,
        at: At,
        clicks: Sequence[Point] = (),
        from_source: bool = True,
    ) -> None:
        """
        A wire drawn from an output port to a corner of a drawn wire ('at', or a new joint
        on a segment), or from the corner to the output port (not 'from_source'). The
        output port joins the line of the drawn wire.
        """
        self._check_new(
            ("port", src_port), ("wire", line_wire), f"{port_key(src_port)} and the wire"
        )
        # Known by a port of the line
        wire = (src_port, line_wire[1])
        self._connect(wire)
        corner = self._corner(line_wire, at)
        self._add(wire, clicks, from_source, join=(line_wire, corner))
        self._complete(src_port)

    def connect_wires(
        self,
        start: tuple[Wire, At],
        line_wire: Wire,
        at: At,
        clicks: Sequence[Point] = (),
    ) -> None:
        """
        A wire drawn from a corner of a drawn wire to a corner of a drawn wire of another
        line (or from and to a new joint on a segment). The lines become one.
        """
        self._check_new(("wire", start[0]), ("wire", line_wire), "The wires")
        wire = (start[0][0], line_wire[1])
        self._connect(wire)
        branch = (start[0], self._corner(*start))
        corner = self._corner(line_wire, at)
        self._add(wire, clicks, True, branch=branch, join=(line_wire, corner))
        self._complete(wire[0])

    # Deleting wires

    def _dependents(self, wire: Wire) -> set[Wire]:
        """The wires that start or end on a wire, and those that start or end on them..."""
        found: set[Wire] = set()
        todo = [wire]
        while todo:
            current = todo.pop()
            for other, (parent, _) in [*self._branches.items(), *self._joins.items()]:
                if parent == current and other not in found:
                    found.add(other)
                    todo.append(other)
        return found

    def _rejoin(
        self, wire: Wire, point: Point, candidates: list[Wire], host: Wire
    ) -> tuple[Wire, int] | None:
        """
        Where a joined wire ends after wires are removed: at the same point, on a wire of
        its line from before. Its own wire if it is still there (its corners can have
        moved), or the wire that took its place, or another wire that runs there. Not on a
        wire that the joined wire's ports reach without it: the wires would make a loop.
        """
        dependents = self._dependents(wire)
        others = self.lines(w for w in self._paths if w != wire and w not in dependents)
        best: tuple[int, Wire, int | None, int] | None = None
        for other in candidates:
            if other == wire or other in dependents or other not in self._paths:
                continue
            if others.same(self._start_node(wire), ("wire", other)):
                continue
            points = self.corner_points(other)
            corner: int | None = None
            segment = -1
            if point in points[1:-1]:
                corner = points.index(point, 1)
            else:
                for index, ((x1, y1), (x2, y2)) in enumerate(pairwise(points)):
                    if (x1 == x2 == point[0] and min(y1, y2) < point[1] < max(y1, y2)) or (
                        y1 == y2 == point[1] and min(x1, x2) < point[0] < max(x1, x2)
                    ):
                        segment = index
                        break
                else:
                    continue
            rank = ((other == host) + (other[0] is host[0]), other, corner, segment)
            if best is None or rank[0] > best[0]:
                best = rank
        if best is None:
            return None
        _, other, corner, segment = best
        if corner is None:
            corner = self.add_joint(other, segment, point, undo=False)
        return other, corner

    def _known_by(
        self, wire: Wire, remaining: list[Wire], lines: Lines, gone: set[Wire]
    ) -> Wire | None:
        """
        Another wire that a joined wire can be known by: to a port of its line that a
        drawn wire reaches, a connection that the line implies if there is one
        """
        drawn = set(remaining)
        found: list[Wire] = []
        for other in remaining:
            for node in (self._start_node(other), self._end_node(other)):
                port = node[1]
                if not isinstance(port, Port):
                    continue
                key = (wire[0], port)
                if (
                    port is not wire[0]
                    and key not in drawn
                    and key not in gone
                    and key not in found
                    and lines.same(("wire", wire), node)
                ):
                    found.append(key)
        return next((key for key in found if key in self._implied), next(iter(found), None))

    def _rekey(self, old: Wire, new: Wire) -> None:
        """
        A drawn wire is known by another port of its line, the old connection is implied
        by the line if its ports are still on it
        """
        self._implied.discard(new)
        if is_connection(old):
            self._implied.add(old)
        self._paths[new] = self._paths.pop(old)
        for anchors in (self._branches, self._joins):
            if old in anchors:
                anchors[new] = anchors.pop(old)
            for other, (parent, corner) in list(anchors.items()):
                if parent == old:
                    anchors[other] = (new, corner)

    def _remove(self, wires: list[Wire], gone: set[Wire]) -> list[Wire]:
        """
        Remove drawn wires, and keep the wires that start or end on them where possible:
        a branch takes the place of a removed wire (see _wire_tree.remove_wires), and a
        joined wire ends on another wire of its line that runs where it ended, or goes too.
        'gone' are connections that are disconnected anyway (of a deleted component).
        Returns the other connections whose ports aren't on the same line any more,
        which must be disconnected.
        """
        old_lines = self.lines()
        # The line that each drawn wire was on, and where each joined wire ends
        line_of = {wire: old_lines.find(("wire", wire)) for wire in self.drawn()}
        points = {
            wire: self.corner_points(host)[corner] for wire, (host, corner) in self._joins.items()
        }
        removing = [wire for wire in wires if wire in self._paths]
        removed: set[Wire] = set()
        # Where the wires start and end, to find the wires that lose a joint
        anchors = {wire: (self._branches.get(wire), self._joins.get(wire)) for wire in self._paths}
        while True:
            if removing:
                # The wires that joined wires end on can go first
                self._fixed_ends = {wire: points[wire] for wire in self._joins}
                try:
                    _wire_tree.remove_wires(
                        self._branches,
                        self._paths,
                        removing,
                        lambda wire, corner: self.corner_points(wire)[corner],
                    )
                finally:
                    self._fixed_ends = {}
                for wire in removing:
                    self._joins.pop(wire, None)
                    removed.add(wire)
                removing = []
            removing = self._settle_joins(points, line_of, removed)
            if removing:
                continue
            # A joined wire is known by a port of its line, another one if it's gone
            remaining = [
                w for w in self.drawn() if w not in removed and (w not in gone or w in self._joins)
            ]
            lines = self.lines(remaining)
            for wire in list(self._joins):
                if wire not in gone and self.is_connected(wire, lines):
                    continue
                other = self._known_by(wire, remaining, lines, gone)
                if other is None:
                    removing.append(wire)
                else:
                    self._rekey(wire, other)
                    points[other] = points.pop(wire)
                    line_of[other] = line_of.pop(wire)
            if not removing:
                break
        lines = self.lines(w for w in self.drawn() if w not in removed and w not in gone)
        disconnect = []
        for wire in self.connections():
            if wire in gone:
                continue
            if wire in removed or wire in self._implied:
                if self.is_connected(wire, lines):
                    # Still on one line, through other wires
                    self._implied.add(wire)
                else:
                    disconnect.append(wire)
        for wire in [*disconnect, *gone]:
            self._implied.discard(wire)
            self._paths.pop(wire, None)
            self._branches.pop(wire, None)
            self._joins.pop(wire, None)
        # The wires where removed wires started or ended, or that start or end elsewhere
        # now, or that took the place of a removed wire
        changed = set()
        for wire, (branch, joint) in anchors.items():
            now = (self._branches.get(wire), self._joins.get(wire))
            if wire in removed or now != (branch, joint):
                changed |= {anchor[0] for anchor in (branch, joint) if anchor is not None}
                changed.add(wire)
        for wire in changed:
            if wire in self._paths:
                self._tidy(wire)
        return disconnect

    def _anchored(self, wire: Wire) -> list[tuple[Wire, dict[Wire, tuple[Wire, int]]]]:
        """The wires that start or end on a wire, and the dict of where (branch or join)"""
        return [
            (other, anchors)
            for anchors in (self._branches, self._joins)
            for other, (parent, _) in anchors.items()
            if parent == wire
        ]

    def _is_unused_joint(self, wire: Wire, segment: int) -> bool:
        """
        Is a segment a joint that no wire starts or ends on: without length, between two
        segments in a straight line that have a length
        """
        path = self.path(wire)
        if not 1 <= segment <= len(path):
            return False
        points = corner_points(self.start_point(wire), self.end_point(wire), path)
        before, at, after = points[segment - 1], points[segment], points[segment + 2]
        # Segment k runs from corner k to corner k + 1
        if points[segment] != points[segment + 1] or at in (before, after):
            return False
        straight = (before[0] == at[0] == after[0]) or (before[1] == at[1] == after[1])
        used = {anchors[other][1] for other, anchors in self._anchored(wire)}
        return straight and not used & {segment, segment + 1}

    def _drop_joint(self, wire: Wire, segment: int) -> None:
        """
        Remove a joint, its segments on each side become one. The only vertical segment
        of a straight wire, that a wire keeps, goes to the end of the wire instead.
        """
        path = list(self._paths[wire])
        if segment < len(path):
            del path[segment - 1 : segment + 1]
        elif len(path) >= 3:
            # The last vertical segment: the one before it reaches the end
            del path[segment - 2 : segment]
        else:
            self._paths[wire] = [self.end_point(wire)[0]]
            return
        self._paths[wire] = path
        for other, anchors in self._anchored(wire):
            parent, corner = anchors[other]
            if corner > segment:
                anchors[other] = (parent, corner - 2)

    def unused_joint(self, wire: Wire, segment: int) -> int | None:
        """
        The joint of a segment, or next to it, that no wire starts or ends on (see
        remove_joint()), None if there is none
        """
        for joint in (segment, segment + 1, segment - 1):
            if self._is_unused_joint(wire, joint):
                return joint
        return None

    def remove_joint(self, wire: Wire, segment: int) -> None:
        """
        Remove a joint of a segment, or next to it, that no wire starts or ends on: the
        segments in a straight line on each side become one (an undo step)
        """
        joint = self.unused_joint(wire, segment)
        if joint is None:
            raise ValueError(f"No joint to remove at segment {segment} of {wire_key(wire)}")
        self._push_undo()
        self._drop_joint(wire, joint)
        self._changed()

    def _tidy(self, wire: Wire) -> None:
        """
        Remove the joints of a wire that no wire starts or ends on. The wire keeps its
        shape.
        """
        segment = 1
        while segment <= len(self._paths[wire]):
            if self._is_unused_joint(wire, segment):
                self._drop_joint(wire, segment)
            else:
                segment += 1

    def _settle_joins(
        self, points: dict[Wire, Point], line_of: dict[Wire, Node], removed: set[Wire]
    ) -> list[Wire]:
        """
        After wires are removed, each joined wire ends where it ended ('points'): on the
        same wire, at its corner there, or on another wire of its line that runs there
        (see _rejoin). The wires are settled in order, each after the wires that it starts
        or ends on, since their shape depends on them. Returns the joined wires that have
        no wire to end on any more.
        """
        settled: set[Wire] = set()
        pending = [wire for wire in self._paths if wire not in removed]
        orphans: list[Wire] = []
        progress = True
        while progress:
            progress = False
            for wire in list(pending):
                branch = self._branches.get(wire)
                joint = self._joins.get(wire)
                if branch is not None and branch[0] not in settled:
                    continue
                if joint is not None:
                    host = joint[0]
                    gone = host in removed or host in orphans or host not in self._paths
                    if not gone and host not in settled:
                        continue
                    candidates = [
                        other
                        for other in settled
                        if line_of.get(other) == line_of.get(wire) and line_of.get(wire)
                    ]
                    new_joint = self._rejoin(wire, points[wire], candidates, host)
                    if new_joint is None:
                        orphans.append(wire)
                        pending.remove(wire)
                        progress = True
                        continue
                    self._joins[wire] = new_joint
                settled.add(wire)
                pending.remove(wire)
                progress = True
        return orphans

    def delete_wires(self, wires: list[Wire]) -> None:
        """
        Delete drawn wires, and disconnect the ports that aren't on the same line any more
        (the other drivers of an input port keep driving it)
        """
        for src_port, dst_port in self._remove(wires, set()):
            src_port.disconnect(dst_port)

    def remove_component(self, component: Component) -> None:
        """
        Forget the wires of a component that is deleted, before it is disconnected, and
        disconnect the other ports that aren't on the same line any more
        """
        gone = {
            wire
            for wire in self.connections()
            if component in (wire[0].parent(), wire[1].parent())
        }
        wires = [
            wire
            for wire in self.drawn()
            if wire[0].parent() is component
            or (wire[1].parent() is component and wire not in self._joins)
        ]
        for src_port, dst_port in self._remove(wires, gone):
            src_port.disconnect(dst_port)

    # The circuit file

    def to_lines(self) -> list[LineDataClass]:
        """
        The lines of the drawn wires as graphs, for the circuit file: their ports, the
        points where the wires turn or meet, and the segments between them
        """
        return self._graphs()[0]

    def _graphs(self) -> tuple[list[LineDataClass], dict[tuple[Wire, int], GraphSegment]]:
        """
        The lines as graphs (see to_lines()), and the segment of a graph that each
        segment of a drawn wire is a part of: the number of the line and its two nodes.
        Not for a segment without length at a node.
        """
        drawn = self.drawing_order()
        lines = self.lines(drawn)
        anchors: dict[Wire, set[int]] = {}
        for wire, (parent, corner) in [*self._branches.items(), *self._joins.items()]:
            anchors.setdefault(parent, set()).add(corner)
        # The node of each corner of a drawn wire, that other wires start or end at
        node_of: dict[tuple[Wire, int], str] = {}
        graphs: dict[Node, LineDataClass] = {}
        segments: dict[Node, set[tuple[str, str]]] = {}
        segment_of: dict[tuple[Wire, int], GraphSegment] = {}
        for wire in drawn:
            root = lines.find(("wire", wire))
            graph = graphs.setdefault(root, LineDataClass(ports=[]))
            number_of_graph = list(graphs).index(root)
            branch, joint = self._branches.get(wire), self._joins.get(wire)
            ends = [
                port_key(wire[0]) if branch is None else node_of[branch],
                port_key(wire[1]) if joint is None else node_of[joint],
            ]
            for end, anchor in zip(ends, (branch, joint), strict=True):
                if anchor is None and end not in graph.ports:
                    graph.ports.append(end)
            points = self.corner_points(wire)
            places = _line_graph.wire_nodes(points, anchors.get(wire, set()))
            nodes = []
            for number, place in enumerate(places):
                if number == 0:
                    node = ends[0]
                elif number == len(places) - 1:
                    node = ends[1]
                else:
                    node = str(len(graph.points) + 1)
                    x, y = points[place[0]]
                    graph.points[node] = [round(x), round(y)]
                for corner in place:
                    node_of[(wire, corner)] = node
                nodes.append(node)
            pairs = segments.setdefault(root, set())
            for first, second in pairwise(nodes):
                if (
                    first != second
                    and (second, first) not in pairs
                    and (first, second) not in pairs
                ):
                    pairs.add((first, second))
                    graph.segments.append([first, second])
            # Segment k of the wire runs from corner k to corner k + 1
            for segment in range(len(points) - 1):
                inside = next(
                    (i for i, place in enumerate(places) if place[0] <= segment < place[-1]),
                    None,
                )
                if inside is not None:
                    continue
                before = max(i for i, place in enumerate(places) if place[-1] <= segment)
                if before + 1 < len(nodes) and nodes[before] != nodes[before + 1]:
                    pair = frozenset((nodes[before], nodes[before + 1]))
                    segment_of[(wire, segment)] = (number_of_graph, pair)
        return list(graphs.values()), segment_of

    def runs(self) -> dict[tuple[Wire, int], GraphSegment]:
        """
        The piece of its line that each segment of a drawn wire is on: the segments of a
        line's graph between its ports and the points where three or more of them meet
        (a click on a wire selects the piece). A piece is known by one of its segments.
        """
        graphs, segment_of = self._graphs()
        pieces = _line_graph.pieces(graphs)
        return {key: pieces[segment] for key, segment in segment_of.items()}

    def delete_runs(self, wires: Iterable[tuple[Wire, int]]) -> None:
        """
        Delete the pieces of lines (see runs()) that segments of drawn wires are on (the
        undo step is the caller's, like for delete_wires()). What is left of a line is one
        line or several, and the ports that no line connects any more are disconnected.
        The drawn wires are made again from the lines, like when a circuit file is loaded.
        """
        graphs, segment_of = self._graphs()
        pieces = _line_graph.pieces(graphs)
        gone = {pieces[segment_of[key]] for key in wires if key in segment_of}
        if not gone:
            return
        new_lines: list[LineDataClass] = []
        for number, graph in enumerate(graphs):
            left = [
                pair for pair in graph.segments if pieces[(number, frozenset(pair))] not in gone
            ]
            new_lines.extend(_line_graph.split_line(graph, left))
        line_of = {name: number for number, line in enumerate(new_lines) for name in line.ports}
        for src_port, dst_port in self.connections():
            src, dst = port_key(src_port), port_key(dst_port)
            if src not in line_of or line_of[src] != line_of.get(dst):
                src_port.disconnect(dst_port)
        self.from_lines(new_lines)
        self._changed()

    def from_lines(self, lines: list[LineDataClass]) -> None:
        """
        Set the drawn wires from the lines of a circuit file, after the components are
        placed and the lines connected (LineDataClass.connect)
        """
        self.clear()
        ports = {port_key(port): port for port in self.ports()}
        for line in lines:
            self._add_line(line, ports)
        # The connections that the lines don't draw are implied by them
        lines_of = self.lines(list(self._paths))
        for wire in self.connections():
            if wire not in self._paths and self.is_connected(wire, lines_of):
                self._implied.add(wire)

    def _add_line(self, line: LineDataClass, ports: dict[str, Port]) -> None:
        """The drawn wires of a line from a circuit file, see _line_graph.decompose()"""
        names = [name for name in line.ports if name in ports]
        # A port of another width isn't connected to the line (see LineDataClass.connect)
        width = LineDataClass.width([ports[name] for name in names])
        names = [name for name in names if ports[name].width == width]
        places: dict[str, Point] = {name: self.port_pos(ports[name]) for name in names}
        for node, point in line.points.items():
            if node not in places and len(point) == 2:
                places[node] = (point[0], point[1])
        segments = [(pair[0], pair[1]) for pair in line.segments if len(pair) == 2]
        outputs = {name for name in names if ports[name].is_output()}
        chains = _line_graph.decompose(names, outputs, places, segments)
        # The wire of each chain, and its nodes from where the wire starts
        wires: list[tuple[Wire, list[str]] | None] = []
        for chain in chains:
            nodes = chain.nodes
            end = ports[nodes[-1]]
            if chain.parent is None:
                start = ports[nodes[0]]
                wire = (start, end)
                if start.is_input() and end.is_output():
                    # From the output port, like a wire drawn between them
                    wire, nodes = (end, start), nodes[::-1]
            else:
                parent = wires[chain.parent]
                wire = (parent[0][0], end) if parent is not None else (end, end)
            if wire[0] is wire[1] or wire in self._paths:
                # Can't be drawn (a wire to its own port)
                wires.append(None)
                continue
            wires.append((wire, nodes))
            self._paths[wire] = []
        keep: dict[int, set[int]] = {}
        for number, chain in enumerate(chains):
            parent = None if chain.parent is None else wires[chain.parent]
            if wires[number] is not None and parent is not None:
                assert chain.parent is not None
                keep.setdefault(chain.parent, set()).add(parent[1].index(chain.nodes[0]))
        corners: dict[int, dict[int, int]] = {}
        for number, chain in enumerate(chains):
            drawn = wires[number]
            if drawn is None:
                continue
            wire, nodes = drawn
            path, corners[number] = _line_graph.polyline_path(
                [places[node] for node in nodes], keep.get(number, set())
            )
            self._paths[wire] = path
            if chain.parent is not None:
                parent = wires[chain.parent]
                assert parent is not None
                corner = corners[chain.parent][parent[1].index(nodes[0])]
                self._branches[wire] = (parent[0], corner)
        # A port that no segment reaches is drawn to another port of the line
        reached = {port for drawn in wires if drawn is not None for port in drawn[0]}
        for name in names:
            port = ports[name]
            other = next((p for p in (ports[n] for n in names) if p in reached), None)
            if port in reached or other is None:
                reached.add(port)
                continue
            wire = (port, other) if port.is_output() and other.is_input() else (other, port)
            if wire not in self._paths:
                self._paths[wire] = self.automatic_path(wire)
                reached.add(port)

    def from_dict(self, wires: dict[str, GuiWireDataClass]) -> None:
        """
        Set the wires from a circuit file, after the components are placed. Wires without
        a valid path in the file get the automatic path, and wires that can't start or
        end where the file says start at the output port or end at the input port.
        """
        self.clear()
        connections = self.connections()
        by_key = {wire_key(wire): wire for wire in connections}
        # The drawn wires that are no connection, "end<start" (see drawn_key)
        ports = {port_key(port): port for port in self.ports()}
        known = set(connections)
        extra: list[Wire] = []
        for key, entry in wires.items():
            if key in by_key or "<" not in key or not entry.drawn:
                continue
            end_name, _, start_name = key.partition("<")
            start_port, end_port = ports.get(start_name), ports.get(end_name)
            if (
                start_port is None
                or end_port is None
                or start_port is end_port
                or start_port.width != end_port.width
                or (start_port, end_port) in known
            ):
                continue
            by_key[key] = (start_port, end_port)
            extra.append((start_port, end_port))
        entries = {wire: wires.get(key) for key, wire in by_key.items()}
        paths: dict[Wire, list[float]] = {}
        for wire, wire_dc in entries.items():
            if wire_dc is not None and not wire_dc.drawn:
                self._implied.add(wire)
            elif wire_dc is not None and is_valid_path(wire_dc.path):
                paths[wire] = list(wire_dc.path)

        def anchor(key: str | None, corner: int | None) -> tuple[Wire, int] | None:
            other = by_key.get(key or "")
            if other is None or corner is None or other in self._implied:
                return None
            if other not in paths or not is_inner_corner(paths[other], corner):
                return None
            return other, corner

        for wire, wire_dc in entries.items():
            if wire_dc is None or wire in self._implied:
                continue
            start = anchor(wire_dc.branch, wire_dc.corner)
            if start is not None and start[0][0] is wire[0]:
                self._branches[wire] = start
            elif start is not None and wire_dc.joint is None:
                # The first files with joined wires had them like a branch
                self._joins[wire] = start
            end = anchor(wire_dc.joint, wire_dc.joint_corner)
            if end is not None:
                self._joins[wire] = end
        self._without_cycles()
        # The first files with joined wires had one for each input port of the line
        seen: set[tuple[Port, Wire, int]] = set()
        for wire, (host, corner) in list(self._joins.items()):
            if (wire[0], host, corner) in seen and wire not in self._branches:
                del self._joins[wire]
                self._implied.add(wire)
            seen.add((wire[0], host, corner))
        self._paths = {wire: path for wire, path in paths.items() if wire not in self._implied}
        for wire in extra:
            # Drawn, the automatic path if the file has none
            self.path(wire)
        # A joined wire is known by a port of its line, else it ends at that port
        lines = self.lines()
        while unknown := [w for w in self._joins if not self.is_connected(w, lines)]:
            for wire in unknown:
                del self._joins[wire]
                self._paths[wire] = self.automatic_path(wire)
            lines = self.lines()
        # A connection that isn't drawn must be implied by a line, else it is drawn
        for wire in [w for w in self._implied if not self.is_connected(w, lines)]:
            self._implied.discard(wire)

    def complete_lines(self) -> list[Wire]:
        """
        Connect each output port of a line to each of its input ports, where a circuit
        file doesn't (a Python circuit file, or a file from before lines). Returns the new
        connections, the ports of different widths are left as they are.
        """
        added: list[Wire] = []
        done: set[Port] = set()
        for port in self.ports():
            if port in done:
                continue
            line = self.line(("port", port))
            done.update(line.outputs, line.inputs)
            for src_port in line.outputs:
                for dst_port in line.inputs:
                    if dst_port in src_port.wired_ports or src_port.width != dst_port.width:
                        continue
                    src_port.wire = dst_port
                    self._implied.add((src_port, dst_port))
                    added.append((src_port, dst_port))
        return added

    def _without_cycles(self) -> None:
        """
        Drop where a wire starts or ends if that would make it start or end on itself,
        through other wires (a broken file)
        """
        resolved: set[Wire] = set()
        pending = set(self._branches) | set(self._joins)
        while True:
            ready = {
                wire
                for wire in pending
                if all(
                    anchor[0] in resolved or anchor[0] not in pending
                    for anchor in (self._branches.get(wire), self._joins.get(wire))
                    if anchor is not None
                )
            }
            if not ready:
                break
            resolved |= ready
            pending -= ready
        for wire in pending:
            self._branches.pop(wire, None)
            self._joins.pop(wire, None)

    def to_dict(self) -> dict[str, GuiWireDataClass]:
        """
        The path of every drawn wire, and where it starts and ends, and the connections
        that are implied, for the circuit file
        """
        wires = {}
        connections = self.connections()
        known = set(connections)
        for wire in connections + [wire for wire in self.drawn() if wire not in known]:
            if wire in self._implied:
                wires[wire_key(wire)] = GuiWireDataClass(path=[], drawn=False)
                continue
            branch = self._branches.get(wire)
            joint = self._joins.get(wire)
            wires[drawn_key(wire)] = GuiWireDataClass(
                path=[round(value) for value in self.path(wire)],
                branch=None if branch is None else drawn_key(branch[0]),
                corner=None if branch is None else branch[1],
                joint=None if joint is None else drawn_key(joint[0]),
                joint_corner=None if joint is None else joint[1],
            )
        return wires
