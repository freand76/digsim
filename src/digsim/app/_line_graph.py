# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""
The lines of wires as graphs, as a circuit file stores them
(kept free from Qt imports so that it can be tested without a display)

A circuit file stores each line as its ports, the points where its wires turn or meet, and
the horizontal and vertical segments between them (see LineDataClass). In the GUI, a line
is drawn wires that start or end on each other (see digsim.app._wire_lines). These are the
steps from one to the other: the nodes of a drawn wire, and the drawn wires of a graph.
"""

from collections.abc import Iterable
from typing import NamedTuple

from digsim.app._wire_path import Point, corner_points
from digsim.storage_model import LineDataClass


def _between(first: float, middle: float, last: float) -> bool:
    return min(first, last) <= middle <= max(first, last)


def _direction(start: Point, end: Point) -> tuple[int, int]:
    """The way from one point to another: (-1, 0, 1) across, and up or down"""
    return (end[0] > start[0]) - (end[0] < start[0]), (end[1] > start[1]) - (end[1] < start[1])


def wire_nodes(points: list[Point], anchors: set[int]) -> list[list[int]]:
    """
    The corners of a drawn wire that are nodes of its line's graph, each with the
    corners at the same place: where it starts, where it turns or where other wires start
    or end on it ('anchors'), and where it ends. A straight run is one segment.
    """
    places: list[list[int]] = []
    for index, point in enumerate(points):
        if places and points[places[-1][0]] == point:
            places[-1].append(index)
        else:
            places.append([index])
    if len(places) == 1:
        # Starts and ends at the same place
        return [places[0], places[0]]
    nodes = [places[0]]
    for before, place, after in zip(places, places[1:], places[2:], strict=False):
        (x1, y1), (x2, y2), (x3, y3) = points[before[0]], points[place[0]], points[after[0]]
        straight = (x1 == x2 == x3 and _between(y1, y2, y3)) or (
            y1 == y2 == y3 and _between(x1, x2, x3)
        )
        if not straight or anchors & set(place):
            nodes.append(place)
    nodes.append(places[-1])
    return nodes


def polyline_path(points: list[Point], keep: set[int]) -> tuple[list[float], dict[int, int]]:
    """
    The path of a wire through points (see digsim.app._wire_path), from the first to the
    last, and the corner of the path at each point in 'keep'. The path is horizontal at
    both ends, and a kept point on a straight run is a corner (a joint).
    """
    corners: list[Point] = [points[0]]
    # The direction of each segment, from corners[i] to corners[i + 1], "H" or "V"
    directions: list[str] = []
    kept_corners: set[int] = set()
    kept: dict[int, int] = {}

    def add(point: Point) -> None:
        last = corners[-1]
        way = _direction(last, point)
        direction = "H" if way[1] == 0 else "V"
        if directions and directions[-1] == direction:
            previous = _direction(corners[-2], last)
            if previous == way and len(corners) - 1 not in kept_corners:
                # On straight
                corners[-1] = point
                return
            # A corner at a kept point, or where the wire goes back: a segment without
            # length across
            corners.append(last)
            directions.append("V" if direction == "H" else "H")
        corners.append(point)
        directions.append(direction)

    for index, point in enumerate(points[1:], start=1):
        last = corners[-1]
        if point != last:
            if point[0] != last[0] and point[1] != last[1]:
                # Not straight: across, then up or down
                add((point[0], last[1]))
            add(point)
        if index in keep and len(corners) > 1:
            kept[index] = len(corners) - 1
            kept_corners.add(len(corners) - 1)
    if not directions:
        directions.append("H")
        corners.append(points[-1])
    if directions[0] == "V":
        # Across from the first point, without length
        corners.insert(1, corners[0])
        directions.insert(0, "H")
        kept = {index: corner + 1 for index, corner in kept.items()}
    if directions[-1] == "V":
        corners.append(corners[-1])
        directions.append("H")
    if len(directions) == 1:
        # Straight across: up or down without length at the end
        corners[1:1] = [corners[1], corners[1]]
    path = [
        corners[index + 1][0] if index % 2 == 0 else corners[index + 1][1]
        for index in range(len(corners) - 3)
    ]
    assert corner_points(corners[0], corners[-1], path) == corners
    return path, kept


class Chain(NamedTuple):
    """
    A drawn wire of a line's graph: its nodes in order, and the chain whose node it starts
    at (None when it starts at a port). It ends at a port.
    """

    nodes: list[str]
    parent: int | None


def _prune(edges: dict[str, set[str]], ports: set[str]) -> None:
    """Remove the loose ends: segments that end at a point no other segment continues from"""
    loose = [node for node, others in edges.items() if node not in ports and len(others) <= 1]
    while loose:
        node = loose.pop()
        for other in edges[node]:
            edges[other].discard(node)
            if other not in ports and len(edges[other]) == 1:
                loose.append(other)
        edges[node] = set()


def _cut_loops(edges: dict[str, set[str]], roots: list[str]) -> None:
    """Remove the segments that close a loop, a line connects its ports once"""
    seen: set[str] = set()
    tree: set[frozenset[str]] = set()
    for root in [*roots, *edges]:
        if root in seen:
            continue
        seen.add(root)
        queue = [root]
        while queue:
            node = queue.pop(0)
            for other in sorted(edges[node]):
                if other not in seen:
                    seen.add(other)
                    tree.add(frozenset((node, other)))
                    queue.append(other)
    for node, others in edges.items():
        others.intersection_update(
            other for other in list(others) if frozenset((node, other)) in tree
        )


def decompose(
    ports: list[str],
    outputs: set[str],
    places: dict[str, Point],
    segments: Iterable[tuple[str, str]],
) -> list[Chain]:
    """
    The drawn wires of a line's graph, its ports ('outputs' among them), the place of
    each node, and its segments. From an output port (or another port), each wire runs
    to a port, straight on where wires meet, and the other ways from there are branches
    of it. A loop is cut, and loose ends are removed.
    """
    port_set = set(ports)
    edges: dict[str, set[str]] = {node: set() for node in places}
    for first, second in segments:
        if first in edges and second in edges and first != second:
            edges[first].add(second)
            edges[second].add(first)
    roots = [port for port in ports if port in outputs] + [
        port for port in ports if port not in outputs
    ]
    _prune(edges, port_set)
    _cut_loops(edges, roots)
    _prune(edges, port_set)

    def order(node: str) -> tuple[int, str]:
        return (ports.index(node), "") if node in port_set else (len(ports), node)

    done: set[frozenset[str]] = set()
    chains: list[Chain] = []
    starts: list[tuple[str, str, int | None]] = []

    def start_at_port(port: str) -> None:
        for other in sorted(edges[port], key=order):
            starts.append((port, other, None))

    def direction(first: str, second: str) -> tuple[int, int]:
        return _direction(places[first], places[second])

    for root in roots:
        start_at_port(root)
        while starts:
            start, first, parent = starts.pop(0)
            if frozenset((start, first)) in done:
                continue
            index = len(chains)
            nodes = [start]
            previous, current = start, first
            done.add(frozenset((start, first)))
            while True:
                nodes.append(current)
                if current in port_set:
                    start_at_port(current)
                    break
                ways = [
                    other
                    for other in sorted(edges[current], key=order)
                    if frozenset((current, other)) not in done
                ]
                if not ways:
                    break
                straight = [
                    other
                    for other in ways
                    if direction(current, other) == direction(previous, current)
                ]
                following = (straight or ways)[0]
                for other in ways:
                    if other != following:
                        starts.append((current, other, index))
                done.add(frozenset((current, following)))
                previous, current = current, following
            chains.append(Chain(nodes, parent))
    return chains


def on_segment(start: Point, end: Point, point: Point) -> bool:
    """Is a point on a horizontal or vertical segment, at an end or between them"""
    return (start[0] == end[0] == point[0] and _between(start[1], point[1], end[1])) or (
        start[1] == end[1] == point[1] and _between(start[0], point[0], end[0])
    )


def ways(point: Point, segments: Iterable[tuple[Point, Point]]) -> set[tuple[int, int]]:
    """
    The ways that segments go from a point (see _direction()): the segments that end at it
    one way, the ones that run through it both ways. Segments without length don't count.
    """
    found: set[tuple[int, int]] = set()
    for start, end in segments:
        if start == end:
            continue
        if point in (start, end):
            found.add(_direction(point, end if point == start else start))
        elif on_segment(start, end, point):
            # Through the point
            found.add(_direction(point, start))
            found.add(_direction(point, end))
    return found


def junctions(segments: Iterable[tuple[Point, Point]]) -> list[Point]:
    """
    Where the segments of a line meet: the ends of segments where the line goes three or
    more ways (a dot in the GUI). Segments without length don't count.
    """
    lengths = [(start, end) for start, end in segments if start != end]
    found: list[Point] = []
    for point in [end for segment in lengths for end in segment]:
        if point not in found and len(ways(point, lengths)) >= 3:
            found.append(point)
    return found


def pieces(
    graphs: list[LineDataClass],
) -> dict[tuple[int, frozenset[str]], tuple[int, frozenset[str]]]:
    """
    The piece of its line that each segment of the lines' graphs is on, by the number
    of the line and the segment's two nodes: the segments between the ports of the line
    and the points where three or more of them meet. A piece is known by one of its
    segments.
    """
    found: dict[tuple[int, frozenset[str]], tuple[int, frozenset[str]]] = {}
    for number, graph in enumerate(graphs):
        pairs = [frozenset(pair) for pair in graph.segments]
        degree: dict[str, int] = {}
        for pair in pairs:
            for node in pair:
                degree[node] = degree.get(node, 0) + 1
        parent = {pair: pair for pair in pairs}

        def find(
            pair: frozenset[str], parent: dict[frozenset[str], frozenset[str]] = parent
        ) -> frozenset[str]:
            while parent[pair] != pair:
                pair = parent[pair]
            return pair

        # The two segments at a node in the middle of a piece are on the same piece
        for node, count in degree.items():
            if count == 2 and node not in graph.ports:
                first, second = (pair for pair in pairs if node in pair)
                parent[find(first)] = find(second)
        for pair in pairs:
            found[(number, pair)] = (number, find(pair))
    return found


def split_line(graph: LineDataClass, segments: list[list[str]]) -> list[LineDataClass]:
    """
    The lines that some of a line's segments make: the parts that are connected and
    reach two ports or more. A part with one port, or none, is gone.
    """
    parent: dict[str, str] = {}

    def find(node: str) -> str:
        parent.setdefault(node, node)
        while parent[node] != node:
            node = parent[node]
        return node

    for first, second in segments:
        parent[find(first)] = find(second)
    parts: dict[str, LineDataClass] = {}
    for first, second in segments:
        part = parts.setdefault(find(first), LineDataClass(ports=[]))
        part.segments.append([first, second])
        for node in (first, second):
            if node in graph.ports:
                if node not in part.ports:
                    part.ports.append(node)
            elif node in graph.points:
                part.points[node] = list(graph.points[node])
    lines = [part for part in parts.values() if len(part.ports) >= 2]
    for line in lines:
        # In the order of the line's ports
        line.ports.sort(key=graph.ports.index)
    return lines


def without_ports(lines: list[LineDataClass], gone: set[str]) -> list[LineDataClass]:
    """
    The lines without some ports, like the ports a changed Verilog module no longer has:
    the segments to them go, back to where the line meets other segments, and a line
    that falls apart is split (see split_line()).
    """
    result: list[LineDataClass] = []
    for line in lines:
        if not gone.intersection(line.ports):
            result.append(line)
            continue
        ports = {port for port in line.ports if port not in gone}
        edges: dict[str, set[str]] = {}
        for first, second in line.segments:
            if first in gone or second in gone:
                continue
            edges.setdefault(first, set()).add(second)
            edges.setdefault(second, set()).add(first)
        _prune(edges, ports)
        segments = [
            [first, second] for first, second in line.segments if second in edges.get(first, ())
        ]
        parts = split_line(line, segments)
        # A port that no segment reaches is drawn to another port of its line
        loose = [
            port for port in line.ports if port in ports and not any(port in s for s in segments)
        ]
        if loose and len(parts) == 1:
            parts[0].ports.extend(loose)
            parts[0].ports.sort(key=line.ports.index)
        elif loose and not parts and len(loose) >= 2:
            parts = [LineDataClass(ports=loose)]
        result.extend(parts)
    return result
