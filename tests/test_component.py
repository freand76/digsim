# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""Pytest module to test the Component base class"""

import pytest

from digsim.circuit import Circuit
from digsim.circuit.components import AND, Bus2Wires, Led, PushButton, StaticValue
from digsim.circuit.components.atoms import ComponentException


def test_reconfigurable_width_dependent_value():
    """A reconfigured value of a bus becomes a slider ('int') up to the bus maximum"""
    circuit = Circuit()
    static_value = StaticValue(circuit, width=4, value=5)
    parameters = static_value.get_reconfigurable_parameters()
    assert parameters["value"]["type"] == "int"
    assert parameters["value"]["min"] == 0
    assert parameters["value"]["max"] == 15
    assert parameters["value"]["default"] == 5
    # The component's own parameters are not changed
    assert StaticValue.get_parameters()["value"]["type"] == "width_pow2"


def test_wire_getter_message():
    """Reading a component's wire gives an error that names the component"""
    circuit = Circuit()
    gate = AND(circuit)
    with pytest.raises(ComponentException, match="Cannot get wire for component 'AND'"):
        _ = gate.wire


def test_update_settings_reconfigures_once():
    """The component is reconfigured once, with all the new settings"""
    reconfigured = []

    class RecordingStaticValue(StaticValue):
        def reconfigure(self):
            reconfigured.append(dict(self._parameters))
            super().reconfigure()

    circuit = Circuit()
    static_value = RecordingStaticValue(circuit, width=4, value=0)
    circuit.init()
    static_value.update_settings({"width": 4, "value": 9})
    assert reconfigured == [{"width": 4, "value": 9, "radix": "dec"}]
    circuit.run(ms=1)
    assert static_value.O.value == 9


def test_disconnect_only_own_wire():
    """Disconnecting a port that another port drives leaves that connection alone"""
    circuit = Circuit()
    driver = PushButton(circuit, "driver")
    other = PushButton(circuit, "other")
    led = Led(circuit, "led")
    driver.O.wire = led.I
    other.O.disconnect(led.I)
    assert led.I.get_driver() is driver.O
    assert driver.O.wired_ports == [led.I]
    driver.O.disconnect(led.I)
    assert not led.I.has_driver()
    assert driver.O.wired_ports == []


@pytest.mark.parametrize("width", [1, 4])
def test_input_without_drivers_is_undefined(width):
    """An input whose last wire is removed is "X", like one that was never connected"""
    circuit = Circuit()
    value = StaticValue(circuit, "value", width=width, value=1)
    sink = Bus2Wires(circuit, "sink", width=width).bus if width > 1 else AND(circuit).A
    value.O.wire = sink
    circuit.init()
    circuit.run(ns=10)
    assert sink.value == 1
    value.O.remove_wires()
    assert sink.value == "X"


@pytest.mark.parametrize(
    ("width", "value", "radix", "text"),
    [
        (16, 0xF000, "dec", "61440"),
        (16, 0xF000, "hex", "0xF000"),
        (6, 5, "hex", "0x05"),
        (4, 5, "bin", "0b0101"),
        (1, 1, "hex", "1"),
    ],
)
def test_static_value_text(width, value, radix, text):
    """A static value is shown in its radix, with all digits for its width"""
    assert StaticValue(Circuit(), width=width, value=value, radix=radix).text() == text


def test_static_value_radix_saved_and_loaded(tmp_path):
    """The radix is saved, decimal if not given, and an unknown radix is an error"""
    circuit = Circuit(name="radix")
    assert StaticValue(circuit, "plain").parameter_get("radix") == "dec"
    StaticValue(circuit, "base", width=16, value=0xE000, radix="hex")
    circuit.to_json_file(tmp_path / "radix.json")
    loaded = Circuit()
    loaded.from_json_file(tmp_path / "radix.json")
    assert loaded.get_component("base").text() == "0xE000"
    with pytest.raises(ComponentException):
        StaticValue(Circuit(), radix="oct")
