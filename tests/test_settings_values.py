# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""Pytest module to test the settings that the settings pane shows and changes"""

import pytest

from digsim.app._settings_values import (
    changes,
    new_settings,
    pane_parameters,
    pane_values,
)
from digsim.circuit import Circuit
from digsim.circuit.components import (
    MUX,
    SRFF,
    Bus2Wires,
    CircuitInput,
    Counter,
    FlipFlop,
    LabelWireIn,
    LabelWireOut,
    Led,
)
from digsim.circuit.components.atoms import ComponentException


def test_values_are_the_components_settings():
    circuit = Circuit()
    counter = Counter(circuit, width=6, enable=True)
    values = pane_values(pane_parameters(counter, circuit))
    assert values == {"width": 6, "enable": True, "up_down": False, "load": False}


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
