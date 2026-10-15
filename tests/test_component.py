# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Pytest module to test the Component base class"""

import pytest

from digsim.circuit import Circuit
from digsim.circuit.components import AND, StaticValue
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
    assert reconfigured == [{"width": 4, "value": 9}]
    circuit.run(ms=1)
    assert static_value.O.value == 9
