# Copyright (c) Fredrik Andersson, 2024-2026
# All rights reserved


import pathlib

import pytest

from digsim.circuit import Circuit
from digsim.circuit.components import Clock, VerilogComponent
from digsim.synth import Synthesis
from digsim.utils import YosysNetlist


# Also on the other platforms: the minimal scope of the tests (see .github/workflows)
pytestmark = pytest.mark.sanity


class DutTester:
    """A helper class to test the up/down counter DUT (Device Under Test)"""

    def __init__(self, circuit, dut, clock):
        self._circuit = circuit
        self._dut = dut
        self._clock = clock
        # Initialize DUT inputs
        self._dut.nrst.value = 0
        self._dut.up.value = 0
        self._dut.down.value = 0

    def reset(self):
        """Reset the DUT, for a clock cycle"""
        self._dut.nrst.value = 0
        self._circuit.run_until_edge(rising=self._clock)
        self._dut.nrst.value = 1

    def clock(self):
        """A clock cycle: to the next rising edge, the counter has its new value"""
        self._circuit.run_until_edge(rising=self._clock)

    def up(self, up):
        """Set the 'up' signal, for the next rising edge"""
        self._dut.up.value = 1 if up else 0

    def down(self, down):
        """Set the 'down' signal, for the next rising edge"""
        self._dut.down.value = 1 if down else 0

    def value(self):
        """Get the counter value"""
        return self._dut.value.value


@pytest.fixture(scope="module")
def current_path():
    """Pytest fixture to get the current path"""
    return pathlib.Path(__file__).parent.relative_to(pathlib.Path.cwd())


@pytest.fixture(scope="module")
def dut(current_path):
    """Pytest fixture to set up the DUT"""
    # Create a new circuit with VCD output
    circuit = Circuit(vcd="up_down_counter_test.vcd")

    # Synthesize the DUT from Verilog
    _dut = VerilogComponent(circuit)
    _dut_synthesis = Synthesis([str(current_path / "up_down_counter.v")], "up_down_counter")
    _yosys_netlist = YosysNetlist(**_dut_synthesis.synth_to_dict())
    _dut.create_from_netlist(_yosys_netlist)

    # A clock of 500 Hz drives the DUT: a period of 2 ms
    clock = Clock(circuit, frequency=500)
    clock.O.wire = _dut.clk

    # Initialize the circuit and yield the DUT tester
    circuit.init()
    yield DutTester(circuit, _dut, clock)


def test_no_count(dut):
    """Test that counting is inactive if neither up or down is enabled"""
    dut.reset()
    assert dut.value() == 0
    dut.up(False)
    dut.down(False)

    for _ in range(10):
        dut.clock()
        assert dut.value() == 0


def test_count_up(dut):
    """Test up counting function"""
    dut.reset()
    assert dut.value() == 0
    dut.up(True)
    dut.down(False)

    for idx in range(1, 16):
        dut.clock()
        assert dut.value() == idx

    # Assert wrap around from 15 to 0
    dut.clock()
    assert dut.value() == 0


def test_count_down(dut):
    """Test down counting function"""
    dut.reset()
    assert dut.value() == 0
    dut.up(False)
    dut.down(True)

    for idx in range(15, -1, -1):
        dut.clock()
        assert dut.value() == idx

    # Assert wrap around from 0 to 15
    dut.clock()
    assert dut.value() == 15


def test_up_precedence(dut):
    """Test up precedence down counting (both up and down enabled)"""
    dut.reset()
    assert dut.value() == 0
    dut.up(True)
    dut.down(True)

    dut.clock()
    assert dut.value() == 1


def test_reset_after_count(dut):
    """Test reset after counting"""
    dut.reset()
    assert dut.value() == 0
    dut.up(True)
    dut.down(False)

    dut.clock()
    assert dut.value() == 1

    dut.clock()
    assert dut.value() == 2

    dut.reset()
    assert dut.value() == 0
