# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Pystest module to test functionality of yosys gates"""

import pytest
from utilities import _H, _L, _X

from digsim.circuit import Circuit
from digsim.circuit.components._yosys_atoms import (
    _AND_,
    _ANDNOT_,
    _AOI3_,
    _AOI4_,
    _BUF_,
    _MUX4_,
    _MUX8_,
    _MUX16_,
    _MUX_,
    _NAND_,
    _NMUX_,
    _NOR_,
    _NOT_,
    _OAI3_,
    _OAI4_,
    _OR_,
    _ORNOT_,
    _XNOR_,
    _XOR_,
)


@pytest.mark.parametrize(
    "test_vector",
    [
        [_L, _L, _L],
        [_L, _H, _L],
        [_H, _L, _L],
        [_H, _H, _H],
    ],
)
def test_yosys_and(test_vector):
    """Test AND gate"""
    circuit = Circuit()
    _dut = _AND_(circuit, "DUT")

    _dut.A.value = test_vector[0]
    _dut.B.value = test_vector[1]
    assert _dut.A.value == test_vector[0]
    assert _dut.B.value == test_vector[1]
    assert _dut.Y.value == "X"
    circuit.run(ms=1)
    assert _dut.Y.value == test_vector[2]


@pytest.mark.parametrize(
    "test_vector",
    [
        [_L, _L, _H],
        [_L, _H, _H],
        [_H, _L, _H],
        [_H, _H, _L],
    ],
)
def test_yosys_nand(test_vector):
    """Test NAND gate"""
    circuit = Circuit()
    _dut = _NAND_(circuit, "DUT")

    _dut.A.value = test_vector[0]
    _dut.B.value = test_vector[1]
    assert _dut.A.value == test_vector[0]
    assert _dut.B.value == test_vector[1]
    assert _dut.Y.value == "X"
    circuit.run(ms=1)
    assert _dut.Y.value == test_vector[2]


@pytest.mark.parametrize(
    "test_vector",
    [
        [_L, _L, _L],
        [_L, _H, _H],
        [_H, _L, _H],
        [_H, _H, _H],
    ],
)
def test_yosys_or(test_vector):
    """Test OR gate"""
    circuit = Circuit()
    _dut = _OR_(circuit, "DUT")

    _dut.A.value = test_vector[0]
    _dut.B.value = test_vector[1]
    assert _dut.A.value == test_vector[0]
    assert _dut.B.value == test_vector[1]
    assert _dut.Y.value == "X"
    circuit.run(ms=1)
    assert _dut.Y.value == test_vector[2]


@pytest.mark.parametrize(
    "test_vector",
    [
        [_L, _L, _H],
        [_L, _H, _L],
        [_H, _L, _L],
        [_H, _H, _L],
    ],
)
def test_yosys_nor(test_vector):
    """Test NOR gate"""
    circuit = Circuit()
    _dut = _NOR_(circuit, "DUT")

    _dut.A.value = test_vector[0]
    _dut.B.value = test_vector[1]
    assert _dut.A.value == test_vector[0]
    assert _dut.B.value == test_vector[1]
    assert _dut.Y.value == "X"
    circuit.run(ms=1)
    assert _dut.Y.value == test_vector[2]


@pytest.mark.parametrize(
    "test_vector",
    [
        [_L, _L, _L],
        [_L, _H, _H],
        [_H, _L, _H],
        [_H, _H, _L],
    ],
)
def test_yosys_xor(test_vector):
    """Test XOR gate"""
    circuit = Circuit()
    _dut = _XOR_(circuit, "DUT")

    _dut.A.value = test_vector[0]
    _dut.B.value = test_vector[1]
    assert _dut.A.value == test_vector[0]
    assert _dut.B.value == test_vector[1]
    assert _dut.Y.value == "X"
    circuit.run(ms=1)
    assert _dut.Y.value == test_vector[2]


@pytest.mark.parametrize(
    "test_vector",
    [
        [_L, _L, _H],
        [_L, _H, _L],
        [_H, _L, _L],
        [_H, _H, _H],
    ],
)
def test_yosys_xnor(test_vector):
    """Test XNOR gate"""
    circuit = Circuit()
    _dut = _XNOR_(circuit, "DUT")

    _dut.A.value = test_vector[0]
    _dut.B.value = test_vector[1]
    assert _dut.A.value == test_vector[0]
    assert _dut.B.value == test_vector[1]
    assert _dut.Y.value == "X"
    circuit.run(ms=1)
    assert _dut.Y.value == test_vector[2]


@pytest.mark.parametrize(
    "test_vector",
    [
        [_L, _L, _L],
        [_L, _H, _L],
        [_H, _L, _H],
        [_H, _H, _L],
    ],
)
def test_yosys_andnot(test_vector):
    """Test ANDNOT gate"""
    circuit = Circuit()
    _dut = _ANDNOT_(circuit, "DUT")

    _dut.A.value = test_vector[0]
    _dut.B.value = test_vector[1]
    assert _dut.A.value == test_vector[0]
    assert _dut.B.value == test_vector[1]
    assert _dut.Y.value == "X"
    circuit.run(ms=1)
    assert _dut.Y.value == test_vector[2]


@pytest.mark.parametrize(
    "test_vector",
    [
        [_L, _L, _H],
        [_L, _H, _L],
        [_H, _L, _H],
        [_H, _H, _H],
    ],
)
def test_yosys_ornot(test_vector):
    """Test ORNOT gate"""
    circuit = Circuit()
    _dut = _ORNOT_(circuit, "DUT")

    _dut.A.value = test_vector[0]
    _dut.B.value = test_vector[1]
    assert _dut.A.value == test_vector[0]
    assert _dut.B.value == test_vector[1]
    assert _dut.Y.value == "X"
    circuit.run(ms=1)
    assert _dut.Y.value == test_vector[2]


@pytest.mark.parametrize(
    "test_vector",
    [
        [_L, _L, _L, _H],
        [_L, _L, _H, _L],
        [_L, _H, _L, _H],
        [_L, _H, _H, _L],
        [_H, _L, _L, _H],
        [_H, _L, _H, _L],
        [_H, _H, _L, _L],
        [_H, _H, _H, _L],
    ],
)
def test_yosys_aoi3(test_vector):
    """Test AOI3 gate"""
    circuit = Circuit()
    _dut = _AOI3_(circuit, "DUT")

    _dut.A.value = test_vector[0]
    _dut.B.value = test_vector[1]
    _dut.C.value = test_vector[2]
    assert _dut.A.value == test_vector[0]
    assert _dut.B.value == test_vector[1]
    assert _dut.C.value == test_vector[2]
    assert _dut.Y.value == "X"
    circuit.run(ms=1)
    assert _dut.Y.value == test_vector[3]


@pytest.mark.parametrize(
    "test_vector",
    [
        [_L, _L, _L, _L, _H],
        [_L, _L, _L, _H, _H],
        [_L, _L, _H, _L, _H],
        [_L, _L, _H, _H, _L],
        [_L, _H, _L, _L, _H],
        [_L, _H, _L, _H, _H],
        [_L, _H, _H, _L, _H],
        [_L, _H, _H, _H, _L],
        [_H, _L, _L, _L, _H],
        [_H, _L, _L, _H, _H],
        [_H, _L, _H, _L, _H],
        [_H, _L, _H, _H, _L],
        [_H, _H, _L, _L, _L],
        [_H, _H, _L, _H, _L],
        [_H, _H, _H, _L, _L],
        [_H, _H, _H, _H, _L],
    ],
)
def test_yosys_aoi4(test_vector):
    """Test AOI4 gate"""
    circuit = Circuit()
    _dut = _AOI4_(circuit, "DUT")

    _dut.A.value = test_vector[0]
    _dut.B.value = test_vector[1]
    _dut.C.value = test_vector[2]
    _dut.D.value = test_vector[3]
    assert _dut.A.value == test_vector[0]
    assert _dut.B.value == test_vector[1]
    assert _dut.C.value == test_vector[2]
    assert _dut.D.value == test_vector[3]
    assert _dut.Y.value == "X"
    circuit.run(ms=1)
    assert _dut.Y.value == test_vector[4]


@pytest.mark.parametrize(
    "test_vector",
    [
        [_L, _L, _L, _H],
        [_L, _L, _H, _H],
        [_L, _H, _L, _H],
        [_L, _H, _H, _L],
        [_H, _L, _L, _H],
        [_H, _L, _H, _L],
        [_H, _H, _L, _H],
        [_H, _H, _H, _L],
    ],
)
def test_yosys_oai3(test_vector):
    """Test OAI3 gate"""
    circuit = Circuit()
    _dut = _OAI3_(circuit, "DUT")

    _dut.A.value = test_vector[0]
    _dut.B.value = test_vector[1]
    _dut.C.value = test_vector[2]
    assert _dut.A.value == test_vector[0]
    assert _dut.B.value == test_vector[1]
    assert _dut.C.value == test_vector[2]
    assert _dut.Y.value == "X"
    circuit.run(ms=1)
    assert _dut.Y.value == test_vector[3]


@pytest.mark.parametrize(
    "test_vector",
    [
        [_L, _L, _L, _L, _H],
        [_L, _L, _L, _H, _H],
        [_L, _L, _H, _L, _H],
        [_L, _L, _H, _H, _H],
        [_L, _H, _L, _L, _H],
        [_L, _H, _L, _H, _L],
        [_L, _H, _H, _L, _L],
        [_L, _H, _H, _H, _L],
        [_H, _L, _L, _L, _H],
        [_H, _L, _L, _H, _L],
        [_H, _L, _H, _L, _L],
        [_H, _L, _H, _H, _L],
        [_H, _H, _L, _L, _H],
        [_H, _H, _L, _H, _L],
        [_H, _H, _H, _L, _L],
        [_H, _H, _H, _H, _L],
    ],
)
def test_yosys_oai4(test_vector):
    """Test OAI4 gate"""
    circuit = Circuit()
    _dut = _OAI4_(circuit, "DUT")

    _dut.A.value = test_vector[0]
    _dut.B.value = test_vector[1]
    _dut.C.value = test_vector[2]
    _dut.D.value = test_vector[3]
    assert _dut.A.value == test_vector[0]
    assert _dut.B.value == test_vector[1]
    assert _dut.C.value == test_vector[2]
    assert _dut.D.value == test_vector[3]
    assert _dut.Y.value == "X"
    circuit.run(ms=1)
    assert _dut.Y.value == test_vector[4]


@pytest.mark.parametrize(
    "test_vector",
    [
        [_L, _H],
        [_H, _L],
    ],
)
def test_yosys_not(test_vector):
    """Test NOT gate"""
    circuit = Circuit()
    _dut = _NOT_(circuit, "DUT")

    _dut.A.value = test_vector[0]
    assert _dut.A.value == test_vector[0]
    assert _dut.Y.value == "X"
    circuit.run(ms=1)
    assert _dut.Y.value == test_vector[1]


@pytest.mark.parametrize(
    "test_vector",
    [
        [_L, _L],
        [_H, _H],
    ],
)
def test_yosys_buf(test_vector):
    """Test BUF gate"""
    circuit = Circuit()
    _dut = _BUF_(circuit, "DUT")

    _dut.A.value = test_vector[0]
    assert _dut.A.value == test_vector[0]
    assert _dut.Y.value == "X"
    circuit.run(ms=1)
    assert _dut.Y.value == test_vector[1]


@pytest.mark.parametrize(
    "test_vector",
    [
        [_X, _L, _L, _X],
        [_L, _L, _L, _L],
        [_H, _L, _L, _H],
        [_L, _X, _H, _X],
        [_L, _L, _H, _L],
        [_L, _H, _H, _H],
    ],
)
def test_yosys_mux(test_vector):
    """Test MUX gate"""
    circuit = Circuit()
    _dut = _MUX_(circuit, "DUT")

    _dut.A.value = test_vector[0]
    _dut.B.value = test_vector[1]
    _dut.S.value = test_vector[2]
    assert _dut.A.value == test_vector[0]
    assert _dut.B.value == test_vector[1]
    assert _dut.S.value == test_vector[2]
    assert _dut.Y.value == "X"
    circuit.run(ms=1)
    assert _dut.Y.value == test_vector[3]


@pytest.mark.parametrize(
    "test_vector",
    [
        [_L, _L, _L, _H],
        [_H, _L, _L, _L],
        [_L, _L, _H, _H],
        [_L, _H, _H, _L],
    ],
)
def test_yosys_nmux(test_vector):
    """Test NMUX gate"""
    circuit = Circuit()
    _dut = _NMUX_(circuit, "DUT")

    _dut.A.value = test_vector[0]
    _dut.B.value = test_vector[1]
    _dut.S.value = test_vector[2]
    assert _dut.A.value == test_vector[0]
    assert _dut.B.value == test_vector[1]
    assert _dut.S.value == test_vector[2]
    assert _dut.Y.value == "X"
    circuit.run(ms=1)
    assert _dut.Y.value == test_vector[3]


@pytest.mark.parametrize(
    "test_vector",
    [
        [_L, _X, _X, _X, _L, _L, _L],
        [_H, _X, _X, _X, _L, _L, _H],
        [_X, _L, _X, _X, _H, _L, _L],
        [_X, _H, _X, _X, _H, _L, _H],
        [_X, _X, _L, _X, _L, _H, _L],
        [_X, _X, _H, _X, _L, _H, _H],
        [_X, _X, _X, _L, _H, _H, _L],
        [_X, _X, _X, _H, _H, _H, _H],
    ],
)
def test_yosys_mux4(test_vector):
    """Test MUX4 gate"""
    circuit = Circuit()
    _dut = _MUX4_(circuit, "DUT")

    _dut.A.value = test_vector[0]
    _dut.B.value = test_vector[1]
    _dut.C.value = test_vector[2]
    _dut.D.value = test_vector[3]
    _dut.S.value = test_vector[4]
    _dut.T.value = test_vector[5]
    assert _dut.A.value == test_vector[0]
    assert _dut.B.value == test_vector[1]
    assert _dut.C.value == test_vector[2]
    assert _dut.D.value == test_vector[3]
    assert _dut.S.value == test_vector[4]
    assert _dut.T.value == test_vector[5]
    assert _dut.Y.value == "X"
    circuit.run(ms=1)
    assert _dut.Y.value == test_vector[6]


@pytest.mark.parametrize(
    "test_vector",
    [
        [_L, _X, _X, _X, _X, _X, _X, _X, _L, _L, _L, _L],
        [_H, _X, _X, _X, _X, _X, _X, _X, _L, _L, _L, _H],
        [_X, _L, _X, _X, _X, _X, _X, _X, _H, _L, _L, _L],
        [_X, _H, _X, _X, _X, _X, _X, _X, _H, _L, _L, _H],
        [_X, _X, _L, _X, _X, _X, _X, _X, _L, _H, _L, _L],
        [_X, _X, _H, _X, _X, _X, _X, _X, _L, _H, _L, _H],
        [_X, _X, _X, _L, _X, _X, _X, _X, _H, _H, _L, _L],
        [_X, _X, _X, _H, _X, _X, _X, _X, _H, _H, _L, _H],
        [_X, _X, _X, _X, _L, _X, _X, _X, _L, _L, _H, _L],
        [_X, _X, _X, _X, _H, _X, _X, _X, _L, _L, _H, _H],
        [_X, _X, _X, _X, _X, _L, _X, _X, _H, _L, _H, _L],
        [_X, _X, _X, _X, _X, _H, _X, _X, _H, _L, _H, _H],
        [_X, _X, _X, _X, _X, _X, _L, _X, _L, _H, _H, _L],
        [_X, _X, _X, _X, _X, _X, _H, _X, _L, _H, _H, _H],
        [_X, _X, _X, _X, _X, _X, _X, _L, _H, _H, _H, _L],
        [_X, _X, _X, _X, _X, _X, _X, _H, _H, _H, _H, _H],
    ],
)
def test_yosys_mux8(test_vector):
    """Test MUX8 gate"""
    circuit = Circuit()
    _dut = _MUX8_(circuit, "DUT")

    _dut.A.value = test_vector[0]
    _dut.B.value = test_vector[1]
    _dut.C.value = test_vector[2]
    _dut.D.value = test_vector[3]
    _dut.E.value = test_vector[4]
    _dut.F.value = test_vector[5]
    _dut.G.value = test_vector[6]
    _dut.H.value = test_vector[7]
    _dut.S.value = test_vector[8]
    _dut.T.value = test_vector[9]
    _dut.U.value = test_vector[10]
    assert _dut.A.value == test_vector[0]
    assert _dut.B.value == test_vector[1]
    assert _dut.C.value == test_vector[2]
    assert _dut.D.value == test_vector[3]
    assert _dut.E.value == test_vector[4]
    assert _dut.F.value == test_vector[5]
    assert _dut.G.value == test_vector[6]
    assert _dut.H.value == test_vector[7]
    assert _dut.S.value == test_vector[8]
    assert _dut.T.value == test_vector[9]
    assert _dut.U.value == test_vector[10]
    assert _dut.Y.value == "X"
    circuit.run(ms=1)
    assert _dut.Y.value == test_vector[11]


@pytest.mark.parametrize(
    "test_vector",
    [
        [_L, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _L, _L, _L, _L, _L],
        [_H, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _L, _L, _L, _L, _H],
        [_X, _L, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _H, _L, _L, _L, _L],
        [_X, _H, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _H, _L, _L, _L, _H],
        [_X, _X, _L, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _L, _H, _L, _L, _L],
        [_X, _X, _H, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _L, _H, _L, _L, _H],
        [_X, _X, _X, _L, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _H, _H, _L, _L, _L],
        [_X, _X, _X, _H, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _H, _H, _L, _L, _H],
        [_X, _X, _X, _X, _L, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _L, _L, _H, _L, _L],
        [_X, _X, _X, _X, _H, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _L, _L, _H, _L, _H],
        [_X, _X, _X, _X, _X, _L, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _H, _L, _H, _L, _L],
        [_X, _X, _X, _X, _X, _H, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _H, _L, _H, _L, _H],
        [_X, _X, _X, _X, _X, _X, _L, _X, _X, _X, _X, _X, _X, _X, _X, _X, _L, _H, _H, _L, _L],
        [_X, _X, _X, _X, _X, _X, _H, _X, _X, _X, _X, _X, _X, _X, _X, _X, _L, _H, _H, _L, _H],
        [_X, _X, _X, _X, _X, _X, _X, _L, _X, _X, _X, _X, _X, _X, _X, _X, _H, _H, _H, _L, _L],
        [_X, _X, _X, _X, _X, _X, _X, _H, _X, _X, _X, _X, _X, _X, _X, _X, _H, _H, _H, _L, _H],
        [_X, _X, _X, _X, _X, _X, _X, _X, _L, _X, _X, _X, _X, _X, _X, _X, _L, _L, _L, _H, _L],
        [_X, _X, _X, _X, _X, _X, _X, _X, _H, _X, _X, _X, _X, _X, _X, _X, _L, _L, _L, _H, _H],
        [_X, _X, _X, _X, _X, _X, _X, _X, _X, _L, _X, _X, _X, _X, _X, _X, _H, _L, _L, _H, _L],
        [_X, _X, _X, _X, _X, _X, _X, _X, _X, _H, _X, _X, _X, _X, _X, _X, _H, _L, _L, _H, _H],
        [_X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _L, _X, _X, _X, _X, _X, _L, _H, _L, _H, _L],
        [_X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _H, _X, _X, _X, _X, _X, _L, _H, _L, _H, _H],
        [_X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _L, _X, _X, _X, _X, _H, _H, _L, _H, _L],
        [_X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _H, _X, _X, _X, _X, _H, _H, _L, _H, _H],
        [_X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _L, _X, _X, _X, _L, _L, _H, _H, _L],
        [_X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _H, _X, _X, _X, _L, _L, _H, _H, _H],
        [_X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _L, _X, _X, _H, _L, _H, _H, _L],
        [_X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _H, _X, _X, _H, _L, _H, _H, _H],
        [_X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _L, _X, _L, _H, _H, _H, _L],
        [_X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _H, _X, _L, _H, _H, _H, _H],
        [_X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _L, _H, _H, _H, _H, _L],
        [_X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _X, _H, _H, _H, _H, _H, _H],
    ],
)
def test_yosys_mux16(test_vector):
    """Test MUX16 gate"""
    circuit = Circuit()
    _dut = _MUX16_(circuit, "DUT")

    _dut.A.value = test_vector[0]
    _dut.B.value = test_vector[1]
    _dut.C.value = test_vector[2]
    _dut.D.value = test_vector[3]
    _dut.E.value = test_vector[4]
    _dut.F.value = test_vector[5]
    _dut.G.value = test_vector[6]
    _dut.H.value = test_vector[7]
    _dut.I.value = test_vector[8]
    _dut.J.value = test_vector[9]
    _dut.K.value = test_vector[10]
    _dut.L.value = test_vector[11]
    _dut.M.value = test_vector[12]
    _dut.N.value = test_vector[13]
    _dut.O.value = test_vector[14]
    _dut.P.value = test_vector[15]
    _dut.S.value = test_vector[16]
    _dut.T.value = test_vector[17]
    _dut.U.value = test_vector[18]
    _dut.V.value = test_vector[19]
    assert _dut.A.value == test_vector[0]
    assert _dut.B.value == test_vector[1]
    assert _dut.C.value == test_vector[2]
    assert _dut.D.value == test_vector[3]
    assert _dut.E.value == test_vector[4]
    assert _dut.F.value == test_vector[5]
    assert _dut.G.value == test_vector[6]
    assert _dut.H.value == test_vector[7]
    assert _dut.I.value == test_vector[8]
    assert _dut.J.value == test_vector[9]
    assert _dut.K.value == test_vector[10]
    assert _dut.L.value == test_vector[11]
    assert _dut.M.value == test_vector[12]
    assert _dut.N.value == test_vector[13]
    assert _dut.O.value == test_vector[14]
    assert _dut.P.value == test_vector[15]
    assert _dut.S.value == test_vector[16]
    assert _dut.T.value == test_vector[17]
    assert _dut.U.value == test_vector[18]
    assert _dut.V.value == test_vector[19]
    assert _dut.Y.value == "X"
    circuit.run(ms=1)
    assert _dut.Y.value == test_vector[20]
