# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""VerilogComponent: a YosysComponent by the name of what it is made from"""

from pathlib import Path

import pytest

from digsim.circuit import Circuit
from digsim.circuit.components import VDD, PushButton, VerilogComponent, YosysComponent


# Also on the other platforms: files and paths (see .github/workflows)
pytestmark = pytest.mark.sanity


COUNTER = Path(__file__).parent.parent / "examples" / "yosys_counter"


def _counter(circuit, path):
    counter = VerilogComponent(circuit, path=path)
    clk = PushButton(circuit, "clk")
    reset = PushButton(circuit, "reset")
    up = VDD(circuit)
    clk.O.wire = counter.clk
    reset.O.wire = counter.reset
    up.O.wire = counter.up
    return counter, clk, reset


def _count(circuit, counter, clk, reset, clocks):
    circuit.init()
    reset.push()
    circuit.run(ms=1)
    reset.release()
    for _ in range(clocks):
        clk.push()
        circuit.run(ms=1)
        clk.release()
        circuit.run(ms=1)
    return counter.cnt.value


@pytest.mark.parametrize("name", ["counter.v", "counter.json"])
def test_verilog_component(name):
    """It is a YosysComponent, built from a Verilog file or a netlist"""
    circuit = Circuit()
    counter, clk, reset = _counter(circuit, COUNTER / name)
    assert isinstance(counter, YosysComponent)
    assert counter.name() == "counter"
    assert _count(circuit, counter, clk, reset, 3) == 3


def test_save_and_load(tmp_path):
    """A saved circuit loads a VerilogComponent again"""
    circuit = Circuit(name="counter")
    _counter(circuit, COUNTER / "counter.json")
    circuit.to_json_file(tmp_path / "counter.circuit")
    loaded = Circuit()
    loaded.from_json_file(tmp_path / "counter.circuit")
    counter = loaded.get_component("counter")
    assert type(counter) is VerilogComponent
    clk = loaded.get_component("clk")
    reset = loaded.get_component("reset")
    assert _count(loaded, counter, clk, reset, 2) == 2
