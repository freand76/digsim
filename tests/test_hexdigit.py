# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Pytest module to test the hex digit component"""

from digsim.circuit import Circuit
from digsim.circuit.components import HexDigit


def test_hexdigit_segments():
    """Each digit shows its own nibble, with the first digit in the high bits"""
    circuit = Circuit()
    hexdigit = HexDigit(circuit, digits=2, dot=True)
    circuit.init()
    assert hexdigit.segments(0) == ""
    hexdigit.val.value = 0x1F
    hexdigit.dot.value = 0b01
    assert hexdigit.segments(0) == "BC"
    assert hexdigit.segments(1) == "AEFG."


def test_hexdigit_dot_default_digit():
    """The dot of a single digit can be read without a digit id"""
    circuit = Circuit()
    hexdigit = HexDigit(circuit, dot=True)
    circuit.init()
    assert not hexdigit.dot_active()
    hexdigit.dot.value = 1
    assert hexdigit.dot_active()
    assert hexdigit.segments() == "."


def test_hexdigit_gui_default():
    """A hex digit added in the GUI has the decimal point of one made in Python"""
    default = HexDigit.get_parameters()["dot"]["default"]
    assert default == HexDigit(Circuit()).parameter_get("dot")
