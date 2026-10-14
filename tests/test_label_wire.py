# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Pytest module to test the label wire components"""

import pytest

from digsim.circuit import Circuit
from digsim.circuit.components import LabelWireIn, LabelWireOut, Led, PushButton
from digsim.circuit.components._label_wire import _LabelWireStorage
from digsim.circuit.components.atoms import DigsimException


@pytest.fixture(autouse=True)
def clear_labels():
    """The label storage is shared, start each test without labels"""
    _LabelWireStorage().clear()


def test_label_wire_connects_driver_to_sink():
    """A signal into a LabelWireIn comes out of the LabelWireOut with the same label"""
    circuit = Circuit()
    button = PushButton(circuit, "button")
    wire_in = LabelWireIn(circuit, "wire_in", label="A")
    # Creating other label components must not forget earlier labels
    LabelWireIn(circuit, "other_in", label="B")
    wire_out = LabelWireOut(circuit, "wire_out", label="A")
    led = Led(circuit, "led")
    button.O.wire = wire_in.A
    wire_out.A.wire = led.I
    circuit.init()

    button.push()
    circuit.run(ms=1)
    assert led.I.value == 1

    button.release()
    circuit.run(ms=1)
    assert led.I.value == 0


def test_label_wire_parameters_keep_labels():
    """Listing parameters (as the GUI settings dialog does) must not forget labels"""
    circuit = Circuit()
    LabelWireIn(circuit, "wire_in", label="A")
    parameters = LabelWireIn.get_parameters()
    assert parameters["label"]["invalid_list"] == ["A"]
    LabelWireOut(circuit, "wire_out", label="A")
    circuit.init()


def test_label_wire_clear():
    """Clearing the circuit removes all labels"""
    circuit = Circuit()
    LabelWireIn(circuit, "wire_in", label="A")
    circuit.clear()
    assert LabelWireIn.get_parameters()["label"]["invalid_list"] == []


def test_label_wire_duplicate_driver_not_added():
    """A LabelWireIn with a label that is already driven is not added to the circuit"""
    circuit = Circuit()
    LabelWireIn(circuit, "wire_in", label="A")
    with pytest.raises(DigsimException):
        LabelWireIn(circuit, "other_in", label="A")
    assert [comp.name() for comp in circuit.components] == ["wire_in"]
