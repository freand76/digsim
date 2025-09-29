# Copyright (c) Fredrik Andersson, 2024-2025
# All rights reserved

import pathlib

import pytest

from digsim.circuit import Circuit
from digsim.circuit.components import YosysComponent
from digsim.synth import Synthesis
from digsim.utils import YosysNetlist


# --- ALU Operation Codes ---
ALU_OP_ADD = 0
ALU_OP_SUB = 1
ALU_OP_AND = 2
ALU_OP_OR = 3
ALU_OP_XOR = 4
ALU_OP_LOGIC_LSHIFT = 5
ALU_OP_LOGIC_RSHIFT = 6
ALU_OP_ARITH_RSHIFT = 7


class DutTester:
    """A helper class to test the ALU DUT (Device Under Test)"""

    def __init__(self, circuit, dut):
        self._circuit = circuit
        self._dut = dut
        # Initialize DUT inputs
        self._dut.A.value = 0
        self._dut.B.value = 0
        self._dut.op.value = 0

    def op(self, op):
        """Set the ALU operation"""
        self._dut.op.value = op
        self._circuit.run(ms=1)

    def operands(self, A, B):
        """Set the ALU operands"""
        self._dut.A.value = A
        self._dut.B.value = B
        self._circuit.run(ms=1)

    def result(self):
        """Get the ALU result"""
        return self._dut.O.value

    def alu_op(self, op, A, B):
        """Helper function to execute a full ALU operation"""
        self.op(op)
        self.operands(A, B)
        return self.result()


@pytest.fixture(scope="module")
def current_path():
    """Pytest fixture to get the current path"""
    return pathlib.Path(__file__).parent.relative_to(pathlib.Path.cwd())


@pytest.fixture(scope="module")
def dut(current_path):
    """Pytest fixture to set up the DUT"""
    # Create a new circuit with VCD output
    circuit = Circuit(vcd="alu_test.vcd")

    # Synthesize the DUT from Verilog
    _dut = YosysComponent(circuit)
    _dut_synthesis = Synthesis([str(current_path / "alu.v")], "alu")
    _yosys_netlist = YosysNetlist(**_dut_synthesis.synth_to_dict())
    _dut.create_from_netlist(_yosys_netlist)

    # Initialize the circuit and yield the DUT tester
    circuit.init()
    yield DutTester(circuit, _dut)


def test_add(dut):
    """Test the ADD operation"""
    assert dut.alu_op(ALU_OP_ADD, 10, 5) == 15


def test_sub(dut):
    """Test the SUB operation"""
    assert dut.alu_op(ALU_OP_SUB, 10, 5) == 5


def test_and(dut):
    """Test the AND operation"""
    assert dut.alu_op(ALU_OP_AND, 0x12, 0xF0) == 0x10


def test_or(dut):
    """Test the OR operation"""
    assert dut.alu_op(ALU_OP_OR, 0x12, 0xF0) == 0xF2


def test_xor(dut):
    """Test the XOR operation"""
    assert dut.alu_op(ALU_OP_XOR, 0x12, 0xF0) == 0xE2


def test_logic_lshift(dut):
    """Test the LOGIC LSHIFT operation"""
    assert dut.alu_op(ALU_OP_LOGIC_LSHIFT, 0x03, 2) == 0x0C


def test_logic_rshift(dut):
    """Test the LOGIC RSHIFT operation"""
    assert dut.alu_op(ALU_OP_LOGIC_RSHIFT, 0x30, 4) == 0x03
    assert dut.alu_op(ALU_OP_LOGIC_RSHIFT, 0xF0, 2) == 0x3C


def test_arith_rshift(dut):
    """Test the ARITH RSHIFT operation"""
    assert dut.alu_op(ALU_OP_ARITH_RSHIFT, 0x30, 4) == 0x03
    assert dut.alu_op(ALU_OP_ARITH_RSHIFT, 0xF0, 2) == 0xFC
