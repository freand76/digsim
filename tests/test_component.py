# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Pytest module to test the Component base class"""

from digsim.circuit import Circuit
from digsim.circuit.components import StaticValue


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
