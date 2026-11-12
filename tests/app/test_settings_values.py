# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""Pytest module to test the settings that the settings pane shows and changes"""

import re

import pytest

from digsim.app._settings_values import (
    NAME_PARAMETER,
    NAME_PATTERN,
    changes,
    frequency_parts,
    frequency_range,
    given_name,
    has_given_name,
    name_problem,
    new_settings,
    pane_parameters,
    pane_values,
    unique_name,
)
from digsim.circuit import Circuit
from digsim.circuit.components import (
    MUX,
    SRFF,
    Bus2Wires,
    CircuitInput,
    Clock,
    Counter,
    FlipFlop,
    IntegratedCircuit,
    LabelWireIn,
    LabelWireOut,
    Led,
)
from digsim.circuit.components.atoms import ComponentException


def test_values_are_the_components_settings():
    circuit = Circuit()
    counter = Counter(circuit, width=6, enable=True)
    values = pane_values(pane_parameters(counter, circuit))
    assert values == {
        "_name": "Counter",
        "width": 6,
        "enable": True,
        "up_down": False,
        "load": False,
    }


def test_the_name_is_first_and_not_taken_by_another():
    circuit = Circuit()
    led = Led(circuit)
    Led(circuit)
    parameters = pane_parameters(led, circuit)
    name = parameters[NAME_PARAMETER]
    assert next(iter(parameters)) == NAME_PARAMETER
    assert name["default"] == "Led"
    assert name["invalid_list"] == ["Led_1"]


@pytest.mark.parametrize(
    ("name", "valid"), [("led", True), ("a b", False), ("a.b", False), ("", False)]
)
def test_name_pattern(name, valid):
    assert (re.fullmatch(NAME_PATTERN, name) is not None) == valid


def test_given_names():
    circuit = Circuit()
    ic = IntegratedCircuit(circuit, "7485")
    led, other_led = Led(circuit), Led(circuit)
    assert given_name(ic) == "ttl_7485"
    assert given_name(led) == "Led"
    assert has_given_name(other_led)
    led.set_name("power")
    assert not has_given_name(led)


def test_unique_name():
    assert unique_name("Led", {"AND"}) == "Led"
    assert unique_name("Led", {"Led", "Led_1"}) == "Led_2"


def test_a_flip_flop_chooses_its_kind():
    circuit = Circuit()
    parameters = pane_parameters(SRFF(circuit), circuit)
    assert parameters["name"]["default"] == "SRFF"


def test_a_label_is_not_taken_by_itself():
    circuit = Circuit()
    sink = LabelWireIn(circuit, label="clk")
    LabelWireIn(circuit, label="data")
    parameter = pane_parameters(sink, circuit)["label"]
    assert "clk" not in parameter["invalid_list"]
    assert "data" in parameter["invalid_list"]


def test_a_port_label_is_not_taken_by_itself():
    circuit = Circuit()
    port = CircuitInput(circuit, label="a")
    assert "a" not in pane_parameters(port, circuit)["label"].get("invalid_list", [])


def test_intrange_shows_its_value():
    circuit = Circuit()
    mux = MUX(circuit, ports=8)
    parameter = pane_parameters(mux, circuit)["ports"]
    assert parameter["range"][parameter["default_index"]] == 8


def test_bits_without_a_setting():
    circuit = Circuit()
    values = pane_values(pane_parameters(Bus2Wires(circuit, width=4), circuit))
    assert values["enable"] is None


def test_changes():
    assert changes({"a": 1, "b": 2}, {"a": 1, "b": 3}) == {"b": 3}
    assert changes({"a": 1}, {"a": 1}) == {}


def test_new_settings_are_the_defaults():
    circuit = Circuit()
    settings = new_settings(Led.get_circuit_parameters(circuit), {})
    assert settings == {"color": "red"}
    assert new_settings(FlipFlop.get_parameters(), {}) == {"name": "SRFF"}
    assert new_settings(MUX.get_parameters(), {})["ports"] == 2


def test_new_label_is_unique():
    circuit = Circuit()
    LabelWireIn(circuit, label="WireLabel")
    settings = new_settings(LabelWireIn.get_circuit_parameters(circuit), {})
    assert settings["label"] == "WireLabelx"


def test_new_wire_source_needs_a_sink():
    circuit = Circuit()
    with pytest.raises(ComponentException, match="to choose from"):
        new_settings(LabelWireOut.get_circuit_parameters(circuit), {})
    LabelWireIn(circuit, label="clk")
    assert new_settings(LabelWireOut.get_circuit_parameters(circuit), {}) == {"label": "clk"}


def test_name_problem():
    circuit = Circuit()
    led, other = Led(circuit), Led(circuit)
    assert name_problem("power", led, circuit) == ""
    assert name_problem("Led", led, circuit) == ""
    assert "another component" in name_problem(other.name(), led, circuit)
    assert "spaces or dots" in name_problem("a.b", led, circuit)
    assert "spaces or dots" in name_problem("", led, circuit)


@pytest.mark.parametrize(
    ("hertz", "parts"),
    [
        (1, (1, "Hz")),
        (999, (999, "Hz")),
        (1_000, (1, "kHz")),
        (1_500, (1_500, "Hz")),
        (250_000, (250, "kHz")),
        (2_000_000, (2, "MHz")),
        (100_000_000, (100, "MHz")),
    ],
)
def test_frequency_parts(hertz, parts):
    """A frequency is shown in the largest unit that it is a whole number of"""
    assert frequency_parts(hertz) == parts


def test_frequency_range():
    """The numbers of each unit stay within the frequencies of the parameter"""
    assert frequency_range("Hz", 1, 100_000_000) == (1, 999)
    assert frequency_range("kHz", 1, 100_000_000) == (1, 999)
    assert frequency_range("MHz", 1, 100_000_000) == (1, 100)
    assert frequency_range("kHz", 1_500, 20_000) == (2, 20)


def test_clock_frequency_is_saved_in_hz():
    """The pane shows the clock's frequency in Hz, the setting it saves"""
    circuit = Circuit()
    clock = Clock(circuit, frequency=2_000_000)
    parameters = pane_parameters(clock, circuit)
    assert parameters["frequency"]["type"] == "frequency"
    assert pane_values(parameters)["frequency"] == 2_000_000
    assert clock.settings_to_dict()["frequency"] == 2_000_000
