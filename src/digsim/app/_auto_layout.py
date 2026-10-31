# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""
Edit > Auto Layout: the components of a circuit placed in columns from its inputs on the
left to its outputs on the right, and its lines drawn again between them, with the layout
of the netlist view (see digsim.app._netlist_layout)
"""

from __future__ import annotations

import dataclasses
from itertools import pairwise

from digsim.app._netlist_layout import NodeShape, Point, Segment, netlist_layout
from digsim.storage_model import LineDataClass
from digsim.utils import Pin


# The space between the circuit and the components that are not wired, below it
UNWIRED_SPACING = 60
UNWIRED_GAP = 40
MIN_ROW_WIDTH = 600
# The space between the stubs to the ports on the top or the bottom of a component
STUB_SPACING = 10.0
# The room between a column of components and the wires next to it
GAP_MARGIN = 40.0


@dataclasses.dataclass
class AutoLayout:
    """Where the components go (the top left corners of their rects), and the new lines"""

    positions: dict[str, tuple[int, int]]
    lines: list[LineDataClass]


def _connections(
    shapes: dict[str, NodeShape], lines: list[tuple[list[str], set[str]]]
) -> list[tuple[Pin, Pin]]:
    """
    The connections of the lines, from one output of each line to its other ports. A port
    on the right of its component (another output of the line) is reached from its own
    side: it is a source too, wired to the first port of the line on the left of its
    component.
    """

    def pin(key: str) -> Pin:
        component, _, port = key.rpartition(".")
        return Pin(component, port)

    connections: list[tuple[Pin, Pin]] = []
    for ports, outputs in lines:
        pins = [pin(key) for key in ports if pin(key).node in shapes]
        if len(pins) < 2:
            continue
        drivers = [p for p, key in zip(pins, ports, strict=False) if key in outputs]
        source = drivers[0] if drivers else pins[0]
        left = [p for p in pins if p != source and shapes[p.node].on_left(p.port)]
        right = [p for p in pins if p != source and not shapes[p.node].on_left(p.port)]
        connections += [(source, sink) for sink in left]
        if left:
            connections += [(extra, left[0]) for extra in right]
    return connections


def _normalized(segments: list[Segment]) -> list[Segment]:
    """
    The segments split where another one ends on them, each once: the wires of a line
    from several sources share their pieces, and meet where one ends on another
    """
    ends = {point for segment in segments for point in segment}
    pieces: dict[Segment, None] = {}
    for start, end in segments:
        if start == end:
            continue
        vertical = start[0] == end[0]
        low, high = sorted((start, end))
        on = sorted(
            point
            for point in ends
            if low <= point <= high
            and (point[0] == start[0] if vertical else point[1] == start[1])
        )
        for first, second in pairwise(on):
            pieces[(first, second)] = None
    return list(pieces)


def _line(
    ports: list[str],
    segments: list[tuple[tuple[int, int], tuple[int, int]]],
    shapes: dict[str, NodeShape],
    positions: dict[str, tuple[int, int]],
) -> LineDataClass:
    """A line of the circuit from its segments: the ends at its ports are the ports"""
    names: dict[tuple[float, float], str] = {}
    for key in ports:
        component, _, port = key.rpartition(".")
        if component in positions and port in shapes[component].pins:
            x, y = positions[component]
            px, py = shapes[component].pins[port]
            names[(round(x + px), round(y + py))] = key
    points: dict[str, list[int]] = {}
    line_segments: list[list[str]] = []
    for segment in _normalized([(a, b) for a, b in segments]):
        ends = []
        for point in segment:
            if point not in names:
                names[point] = f"p{len(points)}"
                points[names[point]] = [int(point[0]), int(point[1])]
            ends.append(names[point])
        line_segments.append(ends)
    return LineDataClass(ports=list(ports), points=points, segments=line_segments)


def _sides(
    shape: NodeShape, directions: dict[str, str], outputs: set[str]
) -> tuple[NodeShape, float, dict[str, list[Point]]]:
    """
    The shape of a component for the layout, which has inputs on the left and outputs on
    the right: a port on the top (or the bottom) is reached from its side, above (or
    below) the component, the port farthest from the side the highest (or lowest), so that
    the stubs don't cross. The space above the component, and the stub of each such port
    from its pin in the layout to the port (from the top of the space).
    """
    up = [port for port, direction in directions.items() if direction == "up"]
    down = [port for port, direction in directions.items() if direction == "down"]
    above = STUB_SPACING * (len(up) + 1) if up else 0.0
    below = STUB_SPACING * (len(down) + 1) if down else 0.0
    pins = {port: (x, y + above) for port, (x, y) in shape.pins.items()}
    stubs: dict[str, list[Point]] = {}
    for ports, sign in ((up, -1), (down, 1)):
        for on_left in (True, False):
            side = [p for p in ports if (p not in outputs) == on_left]
            # The nearest to the side first, nearest the component
            side.sort(key=lambda p: shape.pins[p][0] if on_left else -shape.pins[p][0])
            for rank, port in enumerate(side):
                x, y = shape.pins[port]
                edge = 0.0 if sign < 0 else shape.height
                level = above + edge + sign * STUB_SPACING * (rank + 1)
                pins[port] = (0.0 if on_left else shape.width, level)
                stubs[port] = [pins[port], (x, level), (x, y + above)]
    return NodeShape(shape.width, shape.height + above + below, pins), above, stubs


def auto_layout(
    shapes: dict[str, NodeShape],
    lines: list[tuple[list[str], set[str]]],
    origin: tuple[int, int],
    directions: dict[str, dict[str, str]] | None = None,
) -> AutoLayout:
    """
    Lay out the components ('shapes', by name, their pins by port name) and the lines (the
    ports of each line, "component.port", and the ones that are outputs), with the top
    left corner at 'origin'. The components with no wires go in a row below. The ports
    on the top or the bottom of a component are in 'directions' ("up" or "down"), by
    component and port.
    """
    # In an order of their own, not the order the wires were drawn in: the same circuit
    # gets the same layout, also when it is laid out again
    given = lines
    lines = sorted(
        ((sorted(ports), outputs) for ports, outputs in lines), key=lambda line: line[0]
    )
    real_shapes = shapes
    shapes = dict(shapes)
    above: dict[str, float] = {}
    stubs: dict[str, list[Point]] = {}
    output_keys = {key for _, line_outputs in lines for key in line_outputs}
    for name, port_directions in (directions or {}).items():
        own = {port for port in port_directions if f"{name}.{port}" in output_keys}
        shapes[name], above[name], port_stubs = _sides(shapes[name], port_directions, own)
        stubs.update({f"{name}.{port}": stub for port, stub in port_stubs.items()})
    connections = _connections(shapes, lines)
    sources = {source.node for source, _ in connections}
    sinks = {sink.node for _, sink in connections}
    wired = [name for name in shapes if name in sources | sinks]
    inputs = [name for name in wired if name not in sinks]
    outputs = [name for name in wired if name in sinks and name not in sources]
    # A circuit has no order of its inputs and outputs, like the ports of a module
    layout = netlist_layout(
        {name: shapes[name] for name in wired},
        inputs,
        outputs,
        connections,
        order_ports=True,
        gap_margin=GAP_MARGIN,
        bundles=True,
    )
    # Moved to the origin, in whole pixels: the components start there (the wires and the
    # stubs may be beyond), and a layout of a laid out circuit stays where it is
    left = min((x for x, _ in layout.positions.values()), default=0.0)
    top = min((y + above.get(name, 0.0) for name, (_, y) in layout.positions.items()), default=0.0)

    def moved(point: Point) -> tuple[int, int]:
        return round(point[0] - left + origin[0]), round(point[1] - top + origin[1])

    # The top left corners of the components, below the space of their stubs
    corners = {name: moved(position) for name, position in layout.positions.items()}
    positions = {name: (x, y + round(above.get(name, 0))) for name, (x, y) in corners.items()}
    bottom = max(
        (y + int(real_shapes[name].height) for name, (_, y) in positions.items()),
        default=origin[1],
    )
    # In rows below, as wide as the circuit (or one component)
    right = max(
        (x + int(shapes[name].width) for name, (x, _) in positions.items()),
        default=origin[0] + MIN_ROW_WIDTH,
    )
    right = max(right, origin[0] + MIN_ROW_WIDTH)
    x, y = origin[0], bottom + UNWIRED_SPACING if positions else origin[1]
    row_height = 0
    for name, shape in real_shapes.items():
        if name in positions:
            continue
        if x > origin[0] and x + shape.width > right:
            x, y = origin[0], y + row_height + UNWIRED_GAP
            row_height = 0
        positions[name] = (x, y)
        x += int(shape.width) + UNWIRED_GAP
        row_height = max(row_height, int(shape.height))
    trees = layout.trees()
    new_lines = []
    for ports, _ in given:
        keys = set(ports)
        segments: list[tuple[tuple[int, int], tuple[int, int]]] = [
            (moved(start), moved(end))
            for source, tree in trees.items()
            if f"{source.node}.{source.port}" in keys
            for start, end in tree
        ]
        for key in ports:
            component = key.rpartition(".")[0]
            if key in stubs and component in corners:
                x, y = corners[component]
                stub = [(round(x + px), round(y + py)) for px, py in stubs[key]]
                segments += list(pairwise(stub))
        new_lines.append(_line(ports, segments, real_shapes, positions))
    return AutoLayout(positions, new_lines)
