# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""The layout of the netlist view of a Verilog component"""

from pathlib import Path

import pytest

from digsim.app._netlist_layout import Layout, NodeShape, Point, netlist_layout
from digsim.circuit import Circuit
from digsim.circuit.components import YosysComponent
from digsim.utils import Pin, netlist_graph


pytestmark = pytest.mark.sanity

COUNTER = Path(__file__).parent.parent / "examples" / "yosys_counter" / "counter.v"


def _input() -> NodeShape:
    return NodeShape(40, 20, {"O": (40, 10)})


def _output() -> NodeShape:
    return NodeShape(40, 20, {"I": (0, 10)})


def _cell(inputs: int = 2) -> NodeShape:
    pins = {f"I{index}": (0.0, 10.0 + 20 * index) for index in range(inputs)}
    pins["Y"] = (50.0, 10.0)
    return NodeShape(50, 20 * inputs, pins)


def _pin_point(layout: Layout, nodes: dict[str, NodeShape], pin: Pin) -> Point:
    x, y = layout.positions[pin.node]
    px, py = nodes[pin.node].pins[pin.port]
    return (x + px, y + py)


def _check_wires(layout: Layout, nodes: dict[str, NodeShape]) -> None:
    """Each wire is horizontal and vertical segments, from its source pin to its sink pin"""
    for (source, sink), segments in layout.wires.items():
        assert all(a[0] == b[0] or a[1] == b[1] for a, b in segments), (source, sink)
        neighbors: dict[Point, set[Point]] = {}
        for a, b in segments:
            neighbors.setdefault(a, set()).add(b)
            neighbors.setdefault(b, set()).add(a)
        start = _pin_point(layout, nodes, source)
        end = _pin_point(layout, nodes, sink)
        reached = {start}
        todo = [start]
        while todo:
            for point in neighbors.get(todo.pop(), set()):
                if point not in reached:
                    reached.add(point)
                    todo.append(point)
        assert end in reached, (source, sink)


def test_a_chain_goes_from_left_to_right():
    nodes = {"in": _input(), "a": _cell(1), "b": _cell(1), "out": _output()}
    connections = [
        (Pin("in", "O"), Pin("a", "I0")),
        (Pin("a", "Y"), Pin("b", "I0")),
        (Pin("b", "Y"), Pin("out", "I")),
    ]
    layout = netlist_layout(nodes, ["in"], ["out"], connections)
    xs = [layout.positions[node][0] for node in ("in", "a", "b", "out")]
    assert xs == sorted(xs)
    assert len(set(xs)) == 4
    # In line: the wires are straight
    assert all(len(segments) <= 3 for segments in layout.wires.values())
    assert {layout.positions[node][1] for node in ("in", "a", "b", "out")} == {0.0}
    _check_wires(layout, nodes)


def test_a_wire_that_passes_columns_has_a_slot_in_each():
    nodes = {"in": _input(), "a": _cell(1), "b": _cell(1), "c": _cell(2), "out": _output()}
    connections = [
        (Pin("in", "O"), Pin("a", "I0")),
        (Pin("a", "Y"), Pin("b", "I0")),
        (Pin("b", "Y"), Pin("c", "I0")),
        # Past b, to c
        (Pin("in", "O"), Pin("c", "I1")),
        (Pin("c", "Y"), Pin("out", "I")),
    ]
    layout = netlist_layout(nodes, ["in"], ["out"], connections)
    _check_wires(layout, nodes)
    # Not through a node
    for x, y in [
        point for segment in layout.wires[(Pin("in", "O"), Pin("c", "I1"))] for point in segment
    ]:
        for node in ("a", "b"):
            left, top = layout.positions[node]
            assert not (left < x < left + 50 and top < y < top + 20)


def test_feedback_goes_back_to_the_left():
    # A flip-flop like loop: b drives a, a drives b
    nodes = {"in": _input(), "a": _cell(2), "b": _cell(1), "out": _output()}
    connections = [
        (Pin("in", "O"), Pin("a", "I0")),
        (Pin("a", "Y"), Pin("b", "I0")),
        (Pin("b", "Y"), Pin("a", "I1")),
        (Pin("b", "Y"), Pin("out", "I")),
        # A cell that drives itself
        (Pin("a", "Y"), Pin("a", "I1")),
    ]
    layout = netlist_layout(nodes, ["in"], ["out"], connections)
    assert layout.positions["a"][0] < layout.positions["b"][0]
    _check_wires(layout, nodes)
    back = layout.wires[(Pin("b", "Y"), Pin("a", "I1"))]
    assert min(x for segment in back for x, _ in segment) < layout.positions["a"][0]


def test_an_inout_port_drives_back_from_the_right():
    nodes = {
        "in": _input(),
        "a": _cell(1),
        "b": _cell(1),
        "io": NodeShape(40, 20, {"P": (0, 10)}),
        "out": _output(),
    }
    connections = [
        (Pin("in", "O"), Pin("a", "I0")),
        (Pin("a", "Y"), Pin("io", "P")),
        (Pin("io", "P"), Pin("b", "I0")),
        (Pin("b", "Y"), Pin("out", "I")),
        (Pin("io", "P"), Pin("out", "I")),
    ]
    layout = netlist_layout(nodes, ["in"], ["io", "out"], connections)
    assert layout.positions["io"][0] == layout.positions["out"][0]
    _check_wires(layout, nodes)


def test_the_wires_from_a_pin_share_their_segments():
    nodes = {"in": _input(), **{name: _cell(1) for name in "abc"}, "out": _output()}
    connections = [(Pin("in", "O"), Pin(name, "I0")) for name in "abc"]
    connections.append((Pin("a", "Y"), Pin("out", "I")))
    layout = netlist_layout(nodes, ["in"], ["out"], connections)
    _check_wires(layout, nodes)
    tree = layout.trees()[Pin("in", "O")]
    assert len(tree) < sum(len(layout.wires[(Pin("in", "O"), Pin(n, "I0"))]) for n in "abc")


@pytest.mark.parametrize("functional", [False, True])
def test_the_layout_of_a_counter(functional):
    component = YosysComponent(Circuit(), COUNTER, functional=functional)
    parts = component.netlist_parts()
    cells = {name: cell for name, cell in parts.cells.items() if name in parts.components}
    graph = netlist_graph(parts.ports, cells, parts.nets)
    shapes = {node: NodeShape(40, 20, {node.partition(":")[2]: (40, 10)}) for node in graph.inputs}
    for node in graph.outputs:
        shapes[node] = NodeShape(40, 20, {node.partition(":")[2]: (0, 10)})
    for node in graph.cells:
        cell = cells[node.partition(":")[2]]
        ports = list(cell.connections)
        shapes[node] = NodeShape(
            50,
            20 * len(ports),
            {
                port: (0.0 if cell.port_directions[port] == "input" else 50.0, 10.0 + 20 * i)
                for i, port in enumerate(ports)
            },
        )
    layout = netlist_layout(shapes, graph.inputs, graph.outputs, graph.wires)
    _check_wires(layout, shapes)
    # The inputs left of the cells, the outputs right of them
    cell_xs = [layout.positions[node][0] for node in graph.cells]
    assert max(layout.positions[node][0] for node in graph.inputs) < min(cell_xs)
    assert min(layout.positions[node][0] for node in graph.outputs) > max(cell_xs)
