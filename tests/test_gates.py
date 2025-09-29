# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Pystest module to test functionality of gates"""

import pytest

from digsim.circuit import Circuit
from digsim.circuit.components import AND, DFF, MUX, NAND, NOR, NOT, OR, SR, XOR


@pytest.mark.parametrize(
    "in_a,in_b,out_y",
    [
        ("X", "X", "X"),
        (0, "X", 0),
        (1, "X", "X"),
        (0, 0, 0),
        (0, 1, 0),
        (1, 0, 0),
        (1, 1, 1),
    ],
)
def test_and(in_a, in_b, out_y):
    """Test AND gate"""
    circuit = Circuit()
    _and = AND(circuit)

    _and.A.value = in_a
    _and.B.value = in_b
    assert _and.A.value == in_a
    assert _and.B.value == in_b
    assert _and.Y.value == "X"
    circuit.run(ms=1)
    assert _and.Y.value == out_y


@pytest.mark.parametrize(
    "in_a,in_b,out_y",
    [
        ("X", "X", "X"),
        (1, "X", "X"),
        (0, "X", 1),
        (0, 0, 1),
        (0, 1, 1),
        (1, 0, 1),
        (1, 1, 0),
    ],
)
def test_nand(in_a, in_b, out_y):
    """Test NAND gate"""
    circuit = Circuit()
    _nand = NAND(circuit)

    _nand.A.value = in_a
    _nand.B.value = in_b
    assert _nand.A.value == in_a
    assert _nand.B.value == in_b
    assert _nand.Y.value == "X"
    circuit.run(ms=1)
    assert _nand.Y.value == out_y


@pytest.mark.parametrize(
    "in_a,in_b,out_y",
    [
        ("X", "X", "X"),
        (0, "X", "X"),
        (1, "X", 1),
        (0, 0, 0),
        (0, 1, 1),
        (1, 0, 1),
        (1, 1, 1),
    ],
)
def test_or(in_a, in_b, out_y):
    """Test OR gate"""
    circuit = Circuit()
    _or = OR(circuit)

    _or.A.value = in_a
    _or.B.value = in_b
    assert _or.A.value == in_a
    assert _or.B.value == in_b
    assert _or.Y.value == "X"
    circuit.run(ms=1)
    assert _or.Y.value == out_y


@pytest.mark.parametrize(
    "in_a,in_b,out_y",
    [
        ("X", "X", "X"),
        (0, "X", "X"),
        (1, "X", 0),
        (0, 0, 1),
        (0, 1, 0),
        (1, 0, 0),
        (1, 1, 0),
    ],
)
def test_nor(in_a, in_b, out_y):
    """Test NOR gate"""
    circuit = Circuit()
    _nor = NOR(circuit)

    _nor.A.value = in_a
    _nor.B.value = in_b
    assert _nor.A.value == in_a
    assert _nor.B.value == in_b
    assert _nor.Y.value == "X"
    circuit.run(ms=1)
    assert _nor.Y.value == out_y


@pytest.mark.parametrize(
    "in_a,out_y",
    [
        ("X", "X"),
        (0, 1),
        (1, 0),
    ],
)
def test_not(in_a, out_y):
    """Test NOT gate"""
    circuit = Circuit()
    _not = NOT(circuit)

    _not.A.value = in_a
    assert _not.A.value == in_a
    assert _not.Y.value == "X"
    circuit.run(ms=1)
    assert _not.Y.value == out_y


@pytest.mark.parametrize(
    "in_a,in_b,out_y",
    [
        ("X", "X", "X"),
        (1, "X", "X"),
        (0, "X", "X"),
        (0, 0, 0),
        (0, 1, 1),
        (1, 0, 1),
        (1, 1, 0),
    ],
)
def test_xor(in_a, in_b, out_y):
    """Test XOR gate"""
    circuit = Circuit()
    _xor = XOR(circuit)

    _xor.A.value = in_a
    _xor.B.value = in_b
    assert _xor.A.value == in_a
    assert _xor.B.value == in_b
    assert _xor.Y.value == "X"
    circuit.run(ms=1)
    assert _xor.Y.value == out_y


@pytest.mark.parametrize(
    "in_a,in_b,in_s,out_y",
    [
        ("X", "X", "X", "X"),
        (1, 0, "X", "X"),
        (0, "X", 0, 0),
        (0, "X", 1, "X"),
        (0, 0, 0, 0),
        (1, 0, 0, 1),
        (0, 0, 0, 0),
        (0, 1, 0, 0),
        (0, 0, 1, 0),
        (0, 1, 1, 1),
    ],
)
def test_mux(in_a, in_b, in_s, out_y):
    """Test MUX"""
    circuit = Circuit()
    _mux = MUX(circuit)

    _mux.A.value = in_a
    _mux.B.value = in_b
    _mux.S.value = in_s
    assert _mux.A.value == in_a
    assert _mux.B.value == in_b
    assert _mux.S.value == in_s
    assert _mux.Y.value == "X"
    circuit.run(ms=1)
    assert _mux.Y.value == out_y


def test_sr():
    """Test SR"""
    circuit = Circuit()
    _sr = SR(circuit)

    _sr.S.value = 0
    _sr.R.value = 0
    assert _sr.Q.value == "X"
    assert _sr.nQ.value == "X"
    circuit.run(ms=1)
    assert _sr.Q.value == "X"
    assert _sr.nQ.value == "X"

    # Set
    _sr.S.value = 1
    _sr.R.value = 0
    circuit.run(ms=1)
    assert _sr.Q.value == 1
    assert _sr.nQ.value == 0

    _sr.S.value = 0
    _sr.R.value = 0
    circuit.run(ms=1)
    assert _sr.Q.value == 1
    assert _sr.nQ.value == 0

    # Reset
    _sr.S.value = 0
    _sr.R.value = 1
    circuit.run(ms=1)
    assert _sr.Q.value == 0
    assert _sr.nQ.value == 1

    _sr.S.value = 0
    _sr.R.value = 0
    circuit.run(ms=1)
    assert _sr.Q.value == 0
    assert _sr.nQ.value == 1


def test_dff():
    """Test DFF"""
    circuit = Circuit()
    _dff = DFF(circuit)

    assert _dff.Q.value == "X"

    # No clock, output should be 0
    _dff.C.value = 0
    _dff.D.value = 0
    circuit.run(ms=1)
    assert _dff.Q.value == "X"

    # Clock positive edge, Q <= D (0)
    _dff.C.value = 1
    circuit.run(ms=1)
    assert _dff.Q.value == 0

    # D change without clock edge, Q should not change
    _dff.D.value = 1
    circuit.run(ms=1)
    assert _dff.Q.value == 0

    # Clock negative edge, Q shoule not change
    _dff.C.value = 0
    circuit.run(ms=1)
    assert _dff.Q.value == 0

    # Clock positive edge, Q <= D (1)
    _dff.C.value = 1
    circuit.run(ms=1)
    assert _dff.Q.value == 1


def test_dff_async_reset():
    """Test DFF with asynchronous reset"""
    circuit = Circuit()
    _dff = DFF(circuit, async_reset=True)

    assert _dff.Q.value == "X"

    # No clock, output should be 0
    _dff.C.value = 0
    _dff.D.value = 0
    circuit.run(ms=1)
    assert _dff.Q.value == "X"

    # Async reset high, Q <= 0
    _dff.R.value = 1
    circuit.run(ms=1)
    assert _dff.Q.value == 0

    # D change and positive clock while is reset, Q should not change
    _dff.D.value = 1
    _dff.C.value = 1
    circuit.run(ms=1)
    assert _dff.Q.value == 0

    # Async reset low, Q should not change
    _dff.R.value = 0
    circuit.run(ms=1)
    assert _dff.Q.value == 0

    # Clock negative edge, Q shoule not change
    _dff.C.value = 0
    circuit.run(ms=1)
    assert _dff.Q.value == 0

    # Clock positive edge, Q <= D (1)
    _dff.C.value = 1
    circuit.run(ms=1)
    assert _dff.Q.value == 1


def test_dff_clock_enable():
    """Test DFF with clock enable"""
    circuit = Circuit()
    _dff = DFF(circuit, clock_enable=True)

    assert _dff.Q.value == "X"

    # No clock, No Enable output should be 0
    _dff.C.value = 0
    _dff.D.value = 0
    _dff.E.value = 0
    circuit.run(ms=1)
    assert _dff.Q.value == "X"

    # Clock positive edge without clock enable, Q should not change
    _dff.C.value = 1
    circuit.run(ms=1)
    assert _dff.Q.value == "X"

    # Clock negative edge, Q shoule not change
    _dff.C.value = 0
    circuit.run(ms=1)
    assert _dff.Q.value == "X"

    # Clock enable high, Q shoule not change
    _dff.E.value = 1
    circuit.run(ms=1)
    assert _dff.Q.value == "X"

    # Clock positive edge with clock enable, Q <= D (0)
    _dff.C.value = 1
    circuit.run(ms=1)
    assert _dff.Q.value == 0

    _dff.D.value = 1

    # Clock negative edge, Q shoule not change
    _dff.C.value = 0
    circuit.run(ms=1)
    assert _dff.Q.value == 0

    # Clock positive edge with clock enable, Q <= D (1)
    _dff.C.value = 1
    circuit.run(ms=1)
    assert _dff.Q.value == 1
