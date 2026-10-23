# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""Pytest module to test the LED bar component"""

from digsim.circuit import Circuit
from digsim.circuit.components import LedBar, StaticValue


def test_led_bar_has_an_input_for_each_led():
    """The inputs are named by their LED, from 0"""
    led_bar = LedBar(Circuit(), width=3)
    assert [port.name() for port in led_bar.inports()] == ["0", "1", "2"]
    assert all(port.width == 1 for port in led_bar.inports())


def test_led_bar_shows_its_inputs():
    """Each LED shows its input, LED 0 first"""
    circuit = Circuit()
    high = StaticValue(circuit, value=1)
    low = StaticValue(circuit, value=0)
    led_bar = LedBar(circuit, width=3)
    high.O.wire = led_bar.port("1")
    low.O.wire = led_bar.port("2")
    circuit.init()
    circuit.run(ms=1)
    assert led_bar.lit() == [False, True, False]


def test_led_bar_unknown_input():
    """An LED is off while its input is unknown"""
    circuit = Circuit()
    led_bar = LedBar(circuit, width=3)
    assert led_bar.lit() == [False, False, False]


def test_led_bar_callback():
    """The callback is called when an input changes"""
    changes = []
    circuit = Circuit()
    led_bar = LedBar(circuit, width=2)
    led_bar.set_callback(lambda component: changes.append(component.lit()))
    led_bar.port("0").value = 1
    led_bar.port("1").value = 1
    led_bar.port("0").value = 0
    assert changes == [[True, False], [True, True], [False, True]]


def test_led_bar_saved_and_loaded(tmp_path):
    """The width parameter is restored when a saved circuit is loaded"""
    circuit = Circuit(name="led_bar")
    LedBar(circuit, "bar", width=5)
    circuit.to_json_file(tmp_path / "led_bar.json")
    loaded = Circuit()
    loaded.from_json_file(tmp_path / "led_bar.json")
    assert loaded.get_component("bar").parameter_get("width") == 5
    assert len(loaded.get_component("bar").inports()) == 5
