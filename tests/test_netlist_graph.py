# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""A netlist module as a graph of its ports, cells and the wires between them"""

import json
from pathlib import Path

import pytest

from digsim.circuit import Circuit
from digsim.circuit.components import YosysComponent
from digsim.utils import (
    Pin,
    YosysCell,
    YosysModule,
    YosysNetlist,
    YosysPort,
    cell_node,
    constant_text,
    netlist_graph,
    port_node,
)


COUNTER_NETLIST = Path(__file__).parent.parent / "examples" / "yosys_counter" / "counter.json"


def _counter() -> YosysModule:
    with open(COUNTER_NETLIST, encoding="utf-8") as json_file:
        netlist = YosysNetlist(**json.load(json_file))
    return next(iter(netlist.modules.values()))


def test_the_graph_of_a_counter():
    module = _counter()
    graph = netlist_graph(module.ports, module.cells, module.get_nets())
    assert graph.inputs == [port_node(name, True) for name in ("clk", "reset", "up")]
    assert graph.outputs == [port_node("cnt", False)]
    assert graph.cells == [cell_node(name) for name in module.cells]
    cells = set(graph.cells)
    nodes = cells | set(graph.inputs) | set(graph.outputs)
    for source, sink in graph.wires:
        assert source.node in nodes and sink.node in nodes
    # Each cell is wired, and every bit of the output is driven
    wired = {pin.node for wire in graph.wires for pin in wire}
    assert cells <= wired
    bits = [
        net for (_, sink), nets in graph.wires.items() for net in nets if sink.node == "out:cnt"
    ]
    assert sorted(bits, key=str) == sorted(module.ports["cnt"].bits, key=str)


def test_the_wires_of_cells_that_are_left_out_are_left_out():
    module = _counter()
    left_out = next(iter(module.cells))
    cells = {name: cell for name, cell in module.cells.items() if name != left_out}
    graph = netlist_graph(module.ports, cells, module.get_nets())
    assert cell_node(left_out) not in graph.cells
    assert all(cell_node(left_out) not in (s.node, t.node) for s, t in graph.wires)


def test_a_wire_carries_the_bits_from_one_pin_to_another():
    ports = {
        "a": YosysPort(direction="input", bits=[2, 3]),
        "y": YosysPort(direction="output", bits=[4, 5]),
    }
    cells = {
        "add": YosysCell(
            type="$add",
            port_directions={"A": "input", "B": "input", "Y": "output"},
            connections={"A": [2, 3], "B": ["1", "0"], "Y": [4, 5]},
        )
    }
    module = YosysModule(ports=ports, cells=cells)
    graph = netlist_graph(ports, cells, module.get_nets())
    assert graph.wires == {
        (Pin("in:a", "a"), Pin("cell:add", "A")): [2, 3],
        (Pin("cell:add", "Y"), Pin("out:y", "y")): [4, 5],
    }
    assert graph.constants == {Pin("cell:add", "B"): "2'h1"}


def test_an_inout_port_is_driven_by_cells_and_drives_cells():
    ports = {"io": YosysPort(direction="inout", bits=[2])}
    cells = {
        "buf": YosysCell(
            type="$_TBUF_",
            port_directions={"A": "input", "E": "input", "Y": "output"},
            connections={"A": ["1"], "E": ["0"], "Y": [2]},
        ),
        "not": YosysCell(
            type="$_NOT_",
            port_directions={"A": "input", "Y": "output"},
            connections={"A": [2], "Y": ["x"]},
        ),
    }
    module = YosysModule(ports=ports, cells=cells)
    graph = netlist_graph(ports, cells, module.get_nets())
    assert graph.outputs == [port_node("io", False)]
    assert (Pin("cell:buf", "Y"), Pin("out:io", "io")) in graph.wires
    assert (Pin("out:io", "io"), Pin("cell:not", "A")) in graph.wires


def test_constant_text():
    assert constant_text(["1"]) == "1"
    assert constant_text(["x"]) == "x"
    assert constant_text(["0", "1", "0", "1"]) == "4'hA"
    assert constant_text(["x", "1", "0", "0"]) == "4'b001x"


@pytest.mark.sanity
def test_a_new_build_has_new_parts():
    component = YosysComponent(Circuit(), COUNTER_NETLIST)
    parts = component.netlist_parts()
    component.reload_file()
    assert component.netlist_parts() is not parts
