# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Pytest module to test the names of the GUI wires in the circuit file"""

from digsim.app._wire_key import drawn_key, is_connection, port_key, wire_key
from digsim.circuit import Circuit
from digsim.circuit.components import Led, PushButton, TristateBuffer


def test_wire_key():
    """
    A wire is named by its input port, and by its output port too when the input has
    several drivers, so the circuit files from before tristate wires still load
    """
    circuit = Circuit()
    button = PushButton(circuit, "B")
    led = Led(circuit, "L")
    button.O.wire = led.I
    assert port_key(led.I) == "L.I"
    assert wire_key((button.O, led.I)) == "L.I"
    shared = Led(circuit, "S")
    buffers = [TristateBuffer(circuit, f"T{i}") for i in range(2)]
    buffers[0].Y.wire = shared.I
    assert wire_key((buffers[0].Y, shared.I)) == "S.I"
    buffers[1].Y.wire = shared.I
    assert [wire_key((buffer.Y, shared.I)) for buffer in buffers] == ["S.I<T0.Y", "S.I<T1.Y"]


def test_drawn_key():
    """A drawn wire that is no connection, between two inputs, is named by both ports"""
    circuit = Circuit()
    button = PushButton(circuit, "B")
    leds = [Led(circuit, f"L{i}") for i in range(2)]
    button.O.wire = leds[0].I
    assert is_connection((button.O, leds[0].I))
    assert drawn_key((button.O, leds[0].I)) == "L0.I"
    assert not is_connection((leds[0].I, leds[1].I))
    assert drawn_key((leds[0].I, leds[1].I)) == "L1.I<L0.I"
