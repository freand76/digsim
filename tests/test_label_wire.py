# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Pytest module to test the label wire components"""

import pytest

from digsim.circuit import Circuit
from digsim.circuit.components import LabelWireIn, LabelWireOut, Led, PushButton
from digsim.circuit.components.atoms import DigsimException


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
    parameters = LabelWireIn.get_circuit_parameters(circuit)
    assert parameters["label"]["invalid_list"] == ["A"]
    assert LabelWireOut.get_circuit_parameters(circuit)["label"]["items"] == ["A"]
    LabelWireOut(circuit, "wire_out", label="A")
    circuit.init()


def test_label_wire_clear():
    """Clearing the circuit removes all labels"""
    circuit = Circuit()
    LabelWireIn(circuit, "wire_in", label="A")
    circuit.clear()
    assert LabelWireIn.get_circuit_parameters(circuit)["label"]["invalid_list"] == []


def test_label_wire_duplicate_driver_not_added():
    """A LabelWireIn with a label that is already driven is not added to the circuit"""
    circuit = Circuit()
    LabelWireIn(circuit, "wire_in", label="A")
    with pytest.raises(DigsimException):
        LabelWireIn(circuit, "other_in", label="A")
    assert [comp.name() for comp in circuit.components] == ["wire_in"]


def test_label_wire_same_label_in_two_circuits():
    """Each circuit has its own labels"""
    first = Circuit()
    LabelWireIn(first, "wire_in", label="A")
    second = Circuit()
    LabelWireIn(second, "wire_in", label="A")
    assert LabelWireIn.get_circuit_parameters(second)["label"]["invalid_list"] == ["A"]
    assert LabelWireIn.get_circuit_parameters(Circuit())["label"]["invalid_list"] == []


def test_label_wire_delete_sink():
    """A deleted LabelWireOut is disconnected from its driver"""
    circuit = Circuit()
    wire_in = LabelWireIn(circuit, "wire_in", label="A")
    wire_out = LabelWireOut(circuit, "wire_out", label="A")
    circuit.init()
    assert wire_in.A.wired_ports == [wire_out.A]
    circuit.delete_component(wire_out)
    assert wire_in.A.wired_ports == []


def test_label_wire_delete_driver():
    """A deleted LabelWireIn is disconnected from its sinks, and its label is free again"""
    circuit = Circuit()
    wire_in = LabelWireIn(circuit, "wire_in", label="A")
    wire_out = LabelWireOut(circuit, "wire_out", label="A")
    circuit.init()
    circuit.delete_component(wire_in)
    assert not wire_out.A.has_driver()
    LabelWireIn(circuit, "new_in", label="A")


def test_label_wire_sink_without_driver():
    """A LabelWireOut whose LabelWireIn has been deleted is undefined, the circuit still runs"""
    circuit = Circuit()
    wire_in = LabelWireIn(circuit, "wire_in", label="A")
    wire_out = LabelWireOut(circuit, "wire_out", label="A")
    circuit.init()
    circuit.delete_component(wire_in)
    with pytest.warns(UserWarning, match="no LabelWireIn with the label 'A'"):
        circuit.init()
    circuit.run(ms=1)
    assert wire_out.A.value == "X"


def test_label_wire_mistyped_label_warns():
    """A LabelWireOut with a label that no LabelWireIn has gives a warning"""
    circuit = Circuit()
    LabelWireIn(circuit, "wire_in", label="CLOCK")
    LabelWireOut(circuit, "wire_out", label="CLOKC")
    with pytest.warns(UserWarning, match="'CLOKC'"):
        circuit.init()
