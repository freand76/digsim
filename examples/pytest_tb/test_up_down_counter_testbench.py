# Copyright (c) Fredrik Andersson, 2024
# All rights reserved


import pathlib

import pytest

from digsim.circuit import Circuit
from digsim.circuit.components import YosysComponent
from digsim.synth import Synthesis
from digsim.utils import YosysNetlist


class DutTester:
    def __init__(self, circuit, dut):
        self._circuit = circuit
        self._dut = dut
        self._dut.clk.value = 0
        self._dut.nrst.value = 0
        self._dut.up.value = 0
        self._dut.down.value = 0

    def reset(self):
        self._dut.nrst.value = 0
        self._circuit.run(ms=1)
        self._dut.nrst.value = 1
        self._circuit.run(ms=1)

    def clock(self):
        self._dut.clk.value = 1
        self._circuit.run(ms=1)
        self._dut.clk.value = 0
        self._circuit.run(ms=1)

    def up(self, up):
        self._dut.up.value = 1 if up else 0
        self._circuit.run(ms=1)

    def down(self, down):
        self._dut.down.value = 1 if down else 0
        self._circuit.run(ms=1)

    def value(self):
        return self._dut.value.value


@pytest.fixture(scope="module")
def current_path():
    return pathlib.Path(__file__).parent.relative_to(pathlib.Path.cwd())


@pytest.fixture(scope="module")
def dut(current_path):
    circuit = Circuit(vcd="up_down_counter_test.vcd")

    # Synth DUT
    _dut = YosysComponent(circuit)
    _dut_synthesis = Synthesis([str(current_path / "up_down_counter.v")], "up_down_counter")
    _yosys_netlist = YosysNetlist(**_dut_synthesis.synth_to_dict())
    _dut.create_from_netlist(_yosys_netlist)

    circuit.init()
    yield DutTester(circuit, _dut)


def test_no_count(dut):
    """Test that counting is inactive if neither up or down is enabled"""
    dut.reset()
    assert dut.value() == 0
    dut.up(False)
    dut.down(False)

    for _ in range(0, 10):
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
    """Test up precedence down counting (both up and down enabled)"""
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
