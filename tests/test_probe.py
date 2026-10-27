# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""Pytest module to test the Probe component"""

import pytest

from digsim.circuit import Circuit
from digsim.circuit.components import Probe, StaticValue, TristateBuffer
from digsim.circuit.components.atoms import ComponentException


def _probe(width, radix, value):
    circuit = Circuit()
    source = StaticValue(circuit, width=width, value=value)
    probe = Probe(circuit, width=width, radix=radix)
    source.O.wire = probe.I
    circuit.init()
    return probe


@pytest.mark.parametrize(
    ("width", "radix", "value", "text"),
    [
        (8, "hex", 0x2A, "2A"),
        (12, "hex", 0x5, "005"),
        (8, "dec", 42, "42"),
        (8, "bin", 5, "00000101"),
        (1, "hex", 1, "1"),
        (1, "dec", 0, "0"),
    ],
)
def test_probe_text(width, radix, value, text):
    """The value with all digits for the width, a single bit as 0 or 1"""
    assert _probe(width, radix, value).text() == text


def test_probe_undefined_and_not_driven():
    """An unconnected input is "X", and a line that nothing drives "Z" """
    circuit = Circuit()
    probe = Probe(circuit, width=4)
    buffer = TristateBuffer(circuit, width=4)
    enable = StaticValue(circuit, value=0)
    enable.O.wire = buffer.OE
    buffer.Y.wire = probe.I
    circuit.init()
    circuit.run(ns=10)
    assert probe.text() == "Z"
    assert Probe(Circuit(), width=4).text() == "X"


def test_probe_widest_text():
    """The widest text is the widest value"""
    assert Probe(Circuit(), width=8).widest_text() == "FF"
    assert Probe(Circuit(), width=8, radix="dec").widest_text() == "888"
    assert Probe(Circuit(), width=3, radix="bin").widest_text() == "111"


def test_probe_callback():
    """The callback is called when the value changes"""
    circuit = Circuit()
    source = StaticValue(circuit, width=4, value=3)
    probe = Probe(circuit, width=4)
    source.O.wire = probe.I
    texts = []
    probe.set_callback(lambda component: texts.append(component.text()))
    circuit.init()
    assert texts[-1] == "3"


def test_probe_radix_setting():
    """The radix can be changed, an unknown one gives an error"""
    probe = _probe(4, "hex", 10)
    probe.update_settings({"radix": "dec"})
    probe.reconfigure()
    assert probe.text() == "10"
    with pytest.raises(ComponentException):
        Probe(Circuit(), radix="oct")
