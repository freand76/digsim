# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Pytest module to test the LED bar component"""

from digsim.circuit import Circuit
from digsim.circuit.components import LedBar, StaticValue


def test_led_bar_shows_bits():
    """Each LED shows one bit of the input, bit 0 first"""
    circuit = Circuit()
    value = StaticValue(circuit, width=4, value=0b1010)
    led_bar = LedBar(circuit, width=4)
    value.O.wire = led_bar.I
    circuit.init()
    circuit.run(ms=1)
    assert led_bar.lit() == [False, True, False, True]


def test_led_bar_unknown_input():
    """All LEDs are off while the input is unknown"""
    circuit = Circuit()
    led_bar = LedBar(circuit, width=3)
    assert led_bar.lit() == [False, False, False]


def test_led_bar_callback():
    """The callback is called when the input changes"""
    changes = []
    circuit = Circuit()
    led_bar = LedBar(circuit, width=2)
    led_bar.set_callback(lambda component: changes.append(component.lit()))
    led_bar.I.value = 3
    led_bar.I.value = 1
    assert changes == [[True, True], [True, False]]


def test_led_bar_saved_and_loaded(tmp_path):
    """The width parameter is restored when a saved circuit is loaded"""
    circuit = Circuit(name="led_bar")
    LedBar(circuit, "bar", width=5)
    circuit.to_json_file(tmp_path / "led_bar.json")
    loaded = Circuit()
    loaded.from_json_file(tmp_path / "led_bar.json")
    assert loaded.get_component("bar").parameter_get("width") == 5
