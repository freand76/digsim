# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

import pytest
from digsim.circuit import Circuit
from digsim.circuit.components import AND, NAND, NOT, XOR


UNKNOWN = "X"
HIGH = 1
LOW = 0


@pytest.mark.parametrize(
    "in_a,in_b,out_y",
    [
        (UNKNOWN, UNKNOWN, UNKNOWN),
        (LOW, UNKNOWN, LOW),
        (HIGH, UNKNOWN, UNKNOWN),
        (LOW, LOW, LOW),
        (LOW, HIGH, LOW),
        (HIGH, LOW, LOW),
        (HIGH, HIGH, HIGH),
    ],
)
def test_and(in_a, in_b, out_y):
    circuit = Circuit()
    _and = AND(circuit)

    _and.A.value = in_a
    _and.B.value = in_b
    assert _and.A.value == in_a
    assert _and.B.value == in_b
    assert _and.Y.value == UNKNOWN
    circuit.run(ms=1)
    assert _and.Y.value == out_y


@pytest.mark.parametrize(
    "in_a,out_y",
    [
        (UNKNOWN, UNKNOWN),
        (LOW, HIGH),
        (HIGH, LOW),
    ],
)
def test_not(in_a, out_y):
    circuit = Circuit()
    _not = NOT(circuit)

    _not.A.value = in_a
    assert _not.A.value == in_a
    assert _not.Y.value == UNKNOWN
    circuit.run(ms=1)
    assert _not.Y.value == out_y


@pytest.mark.parametrize(
    "in_a,in_b,out_y",
    [
        (UNKNOWN, UNKNOWN, UNKNOWN),
        (HIGH, UNKNOWN, UNKNOWN),
        (LOW, UNKNOWN, HIGH),
        (LOW, LOW, HIGH),
        (LOW, HIGH, HIGH),
        (HIGH, LOW, HIGH),
        (HIGH, HIGH, LOW),
    ],
)
def test_nand(in_a, in_b, out_y):
    circuit = Circuit()
    _nand = NAND(circuit)

    _nand.A.value = in_a
    _nand.B.value = in_b
    assert _nand.A.value == in_a
    assert _nand.B.value == in_b
    assert _nand.Y.value == UNKNOWN
    circuit.run(ms=1)
    assert _nand.Y.value == out_y


@pytest.mark.parametrize(
    "in_a,in_b,out_y",
    [
        (UNKNOWN, UNKNOWN, UNKNOWN),
        (HIGH, UNKNOWN, UNKNOWN),
        (LOW, UNKNOWN, UNKNOWN),
        (LOW, LOW, LOW),
        (LOW, HIGH, HIGH),
        (HIGH, LOW, HIGH),
        (HIGH, HIGH, LOW),
    ],
)
def test_xor(in_a, in_b, out_y):
    circuit = Circuit()
    _xor = XOR(circuit)

    _xor.A.value = in_a
    _xor.B.value = in_b
    assert _xor.A.value == in_a
    assert _xor.B.value == in_b
    assert _xor.Y.value == UNKNOWN
    circuit.run(ms=1)
    assert _xor.Y.value == out_y
