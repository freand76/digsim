# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""
Pytest module to test the compiled blocks of the native engine: a Yosys component is
simulated as one block, without delays inside, and must work like it does in the Python
engine (the tests run with both engines). A netlist that can't be a block keeps its cells.
"""

import pytest

from digsim.circuit import Circuit, _native
from digsim.circuit.components import GND, VDD, YosysComponent
from digsim.circuit.components.atoms import Component, PortIn
from digsim.utils import YosysNetlist


pytestmark = pytest.mark.sanity

NATIVE = _native.mode() == "native"


def _netlist(ports, cells, netnames=None):
    """A netlist of one module: ports {name: (direction, bits)}, cells {name: (type,
    connections {port: (direction, bits)}, parameters)}, netnames {name: (bits, init)}"""
    return YosysNetlist(
        modules={
            "top": {
                "ports": {
                    name: {"direction": direction, "bits": bits}
                    for name, (direction, bits) in ports.items()
                },
                "cells": {
                    name: {
                        "type": kind,
                        "port_directions": {p: d for p, (d, _) in connections.items()},
                        "connections": {p: bits for p, (_, bits) in connections.items()},
                        "parameters": {p: format(v, "b") for p, v in parameters.items()},
                    }
                    for name, (kind, connections, parameters) in cells.items()
                },
                "netnames": {
                    name: {"bits": bits, "attributes": {"init": init}}
                    for name, (bits, init) in (netnames or {}).items()
                },
            }
        }
    )


def _counter(init=None):
    """A 4-bit counter with a synchronous reset: q <= rst ? 0 : q + 1, q starts at init
    (a binary string, "X" without)"""
    q, plus, d = [2, 3, 4, 5], [6, 7, 8, 9], [10, 11, 12, 13]
    ports = {"clk": ("input", [14]), "rst": ("input", [15]), "q": ("output", q)}
    word = {"A_SIGNED": 0, "B_SIGNED": 0, "A_WIDTH": 4, "B_WIDTH": 4, "Y_WIDTH": 4}
    cells = {
        "add": (
            "$add",
            {"A": ("input", q), "B": ("input", ["1", "0", "0", "0"]), "Y": ("output", plus)},
            word,
        ),
        "mux": (
            "$mux",
            {
                "A": ("input", plus),
                "B": ("input", ["0"] * 4),
                "S": ("input", [15]),
                "Y": ("output", d),
            },
            {"WIDTH": 4},
        ),
        "reg": (
            "$dff",
            {"CLK": ("input", [14]), "D": ("input", d), "Q": ("output", q)},
            {"WIDTH": 4, "CLK_POLARITY": 1},
        ),
    }
    return _netlist(ports, cells, None if init is None else {"q": (q, init)})


def _component(netlist):
    circuit = Circuit()
    component = YosysComponent(circuit)
    component.create_from_netlist(netlist)
    circuit.init()
    return circuit, component


def _reset(circuit, component):
    """Reset the counter: the reset settles before the clock edge"""
    component.rst.value = 1
    circuit.run(ns=100)
    _clock(circuit, component)
    component.rst.value = 0
    circuit.run(ns=100)


def _clock(circuit, component, cycles=1):
    for _ in range(cycles):
        component.clk.value = 1
        circuit.run(ns=100)
        component.clk.value = 0
        circuit.run(ns=100)


class _Sink(Component):
    """A component with an input that does nothing"""

    def __init__(self, circuit):
        super().__init__(circuit, "sink")
        self.add_port(PortIn(self, "i", width=4))

    def update(self):
        pass


def test_counter_is_one_block():
    """The cells of the counter are one block, and it counts like with the cells"""
    circuit, component = _component(_counter())
    if NATIVE:
        assert len(circuit._engine.blocks) == 1
    _reset(circuit, component)
    assert component.q.value == 0
    for count in range(1, 20):
        _clock(circuit, component)
        assert component.q.value == count % 16


def test_cells_inside_read_the_block():
    """The ports of the cells of a block have the values of the block"""
    circuit, component = _component(_counter())
    _reset(circuit, component)
    _clock(circuit, component, 5)
    register = component.netlist_parts().components["reg"]
    assert [register.port(f"Q[{bit}]").value for bit in range(4)] == [1, 0, 1, 0]


def test_new_wire_hands_the_block_to_python():
    """A new wire in the middle of a clock cycle: the counter counts on in Python"""
    circuit, component = _component(_counter())
    _reset(circuit, component)
    _clock(circuit, component, 3)
    # The rising edge, and a wire before the register's output changes
    component.clk.value = 1
    sink = _Sink(circuit)
    component.q.wire = sink.i
    circuit.run(ns=100)
    assert circuit._engine is None
    assert component.q.value == 4
    component.clk.value = 0
    circuit.run(ns=100)
    for count in range(5, 12):
        _clock(circuit, component)
        assert component.q.value == count
        assert sink.i.value == count


def test_blocks_off(monkeypatch):
    """With DIGSIM_BLOCKS=0 the native engine keeps the cells, with their delays"""
    monkeypatch.setenv("DIGSIM_BLOCKS", "0")
    circuit, component = _component(_counter())
    if NATIVE:
        assert not circuit._engine.blocks
    _reset(circuit, component)
    _clock(circuit, component, 7)
    assert component.q.value == 7


def test_loop_keeps_the_cells():
    """A combinational loop (a NAND latch) can't be a block, and still works"""
    ports = {"s_n": ("input", [2]), "r_n": ("input", [3]), "q": ("output", [4])}
    cells = {
        "n1": ("$_NAND_", {"A": ("input", [2]), "B": ("input", [5]), "Y": ("output", [4])}, {}),
        "n2": ("$_NAND_", {"A": ("input", [3]), "B": ("input", [4]), "Y": ("output", [5])}, {}),
    }
    circuit, component = _component(_netlist(ports, cells))
    if NATIVE:
        assert not circuit._engine.blocks
    component.s_n.value = 0
    component.r_n.value = 1
    circuit.run(ns=100)
    assert component.q.value == 1
    component.s_n.value = 1
    circuit.run(ns=100)
    assert component.q.value == 1
    component.r_n.value = 0
    circuit.run(ns=100)
    assert component.q.value == 0


def test_tristate_keeps_the_cells():
    """A tristate buffer can't be in a block"""
    ports = {"a": ("input", [2]), "en": ("input", [3]), "y": ("output", [4])}
    cells = {
        "t": (
            "$tribuf",
            {"A": ("input", [2]), "EN": ("input", [3]), "Y": ("output", [4])},
            {"WIDTH": 1},
        ),
    }
    circuit, component = _component(_netlist(ports, cells))
    if NATIVE:
        assert not circuit._engine.blocks
    component.a.value = 1
    component.en.value = 1
    circuit.run(ns=100)
    assert component.y.value == 1
    component.en.value = 0
    circuit.run(ns=100)
    assert component.y.value == "Z"


def test_latch_sees_data_before_enable():
    """A latch whose data and enable change in the same word: the bits change one at a
    time, the lowest first, like in Python (the data, then the enable closes)"""
    ports = {"in": ("input", [2, 3]), "q": ("output", [4])}
    cells = {
        "latch": (
            "$dlatch",
            {"EN": ("input", [3]), "D": ("input", [2]), "Q": ("output", [4])},
            {"WIDTH": 1, "EN_POLARITY": 1},
        ),
    }
    circuit, component = _component(_netlist(ports, cells))
    component.port("in").value = 0b11
    circuit.run(ns=100)
    assert component.q.value == 1
    component.port("in").value = 0b00
    circuit.run(ns=100)
    assert component.q.value == 0


def test_gnd_and_vdd_next_to_a_block():
    """GND and VDD outside a block (their outputs can't be driven, like the outputs of the
    cells in a block) drive the inputs of a block"""
    circuit = Circuit()
    component = YosysComponent(circuit)
    component.create_from_netlist(_counter(init="0000"))
    vdd = VDD(circuit)
    gnd = GND(circuit)
    vdd.O.wire = component.rst
    circuit.init()
    circuit.run(ns=100)
    _clock(circuit, component)
    assert component.q.value == 0
    vdd.O.disconnect(component.rst)
    gnd.O.wire = component.rst
    circuit.init()
    circuit.run(ns=100)
    _clock(circuit, component, 3)
    assert component.q.value == 3
