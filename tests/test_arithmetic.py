# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""Pytest module to test the arithmetic components"""

import pytest

from digsim.circuit import Circuit
from digsim.circuit.components import (
    Adder,
    Comparator,
    Multiplier,
    Negator,
    StaticValue,
    Subtractor,
)
from digsim.circuit.components.atoms import ComponentException


def _drive(circuit, port, value):
    """A static value on an input"""
    source = StaticValue(circuit, width=port.width, value=value)
    source.O.wire = port


def _run(circuit):
    circuit.init()
    circuit.run(ns=10)


@pytest.mark.parametrize(
    ("a", "b", "carry", "s", "cout"),
    [(3, 4, 0, 7, 0), (200, 100, 0, 44, 1), (255, 0, 1, 0, 1), (0, 0, 1, 1, 0)],
)
def test_adder(a, b, carry, s, cout):
    circuit = Circuit()
    adder = Adder(circuit, width=8, carry_in=True)
    _drive(circuit, adder.A, a)
    _drive(circuit, adder.B, b)
    _drive(circuit, adder.Cin, carry)
    _run(circuit)
    assert (adder.S.value, adder.Cout.value) == (s, cout)


def test_adder_without_carry_in():
    """Without Cin the adder adds A and B, an unconnected input gives X"""
    circuit = Circuit()
    adder = Adder(circuit, width=4)
    assert "Cin" not in [port.name() for port in adder.ports]
    _drive(circuit, adder.A, 9)
    _run(circuit)
    assert adder.S.value == "X"
    _drive(circuit, adder.B, 9)
    _run(circuit)
    assert (adder.S.value, adder.Cout.value) == (2, 1)


@pytest.mark.parametrize(
    ("a", "b", "borrow", "d", "bout"),
    [(7, 3, 0, 4, 0), (3, 7, 0, 252, 1), (5, 5, 1, 255, 1), (5, 4, 1, 0, 0)],
)
def test_subtractor(a, b, borrow, d, bout):
    circuit = Circuit()
    subtractor = Subtractor(circuit, width=8, borrow_in=True)
    _drive(circuit, subtractor.A, a)
    _drive(circuit, subtractor.B, b)
    _drive(circuit, subtractor.Bin, borrow)
    _run(circuit)
    assert (subtractor.D.value, subtractor.Bout.value) == (d, bout)


def test_multiplier():
    """The product is twice as wide as the inputs"""
    circuit = Circuit()
    multiplier = Multiplier(circuit, width=8)
    assert multiplier.P.width == 16
    _drive(circuit, multiplier.A, 255)
    _drive(circuit, multiplier.B, 255)
    _run(circuit)
    assert multiplier.P.value == 65025
    with pytest.raises(ComponentException):
        Multiplier(Circuit(), width=17)


@pytest.mark.parametrize(
    ("signed", "a", "b", "flags"),
    [
        (False, 3, 5, (1, 0, 0)),
        (False, 5, 5, (0, 1, 0)),
        (False, 0xFF, 1, (0, 0, 1)),
        (True, 0xFF, 1, (1, 0, 0)),
        (True, 0x80, 0x7F, (1, 0, 0)),
    ],
)
def test_comparator(signed, a, b, flags):
    """Unsigned 0xFF is 255, signed -1"""
    circuit = Circuit()
    comparator = Comparator(circuit, width=8, signed=signed)
    _drive(circuit, comparator.A, a)
    _drive(circuit, comparator.B, b)
    _run(circuit)
    assert (comparator.LT.value, comparator.EQ.value, comparator.GT.value) == flags


@pytest.mark.parametrize(("a", "y"), [(1, 255), (0, 0), (128, 128), (255, 1)])
def test_negator(a, y):
    circuit = Circuit()
    negator = Negator(circuit, width=8)
    _drive(circuit, negator.A, a)
    _run(circuit)
    assert negator.Y.value == y
