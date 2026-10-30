# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""Pytest module to test the label wire components"""

import pytest

from digsim.circuit import Circuit
from digsim.circuit.components import (
    CircuitInput,
    CircuitOutput,
    LabelWireIn,
    LabelWireOut,
    Led,
    PushButton,
    StaticValue,
    SubCircuit,
)
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


def _label_pass(path, sink_only=False):
    """A circuit file, y = a through the label wire 'clk' (or only a LabelWireOut 'clk')"""
    circuit = Circuit(name=path.stem)
    a = CircuitInput(circuit, label="a")
    y = CircuitOutput(circuit, label="y")
    if not sink_only:
        wire_in = LabelWireIn(circuit, "clk_in", label="clk")
        a.port("a").wire = wire_in.port("clk")
    wire_out = LabelWireOut(circuit, "clk_out", label="clk")
    wire_out.port("clk").wire = y.port("y")
    circuit.to_json_file(path)
    return path


def _top_label(circuit, value):
    """The top-level label wire 'clk', driven by a value, and a sink of it"""
    wire_in = LabelWireIn(circuit, "clk_in", label="clk")
    StaticValue(circuit, value=value).O.wire = wire_in.port("clk")
    return LabelWireOut(circuit, "clk_out", label="clk")


@pytest.mark.sanity
def test_label_wires_of_a_subcircuit_are_its_own(tmp_path):
    """Two instances of a file with the label 'clk', in a circuit with its own 'clk'"""
    path = _label_pass(tmp_path / "label_pass.circuit")
    circuit = Circuit(name="top")
    top_out = _top_label(circuit, 1)
    first = SubCircuit(circuit, path)
    second = SubCircuit(circuit, path)
    StaticValue(circuit, value=0).O.wire = first.a
    StaticValue(circuit, value=1).O.wire = second.a
    circuit.init()
    circuit.run(ns=100)
    assert (first.y.value, second.y.value) == (0, 1)
    assert top_out.port("clk").value == 1
    # The labels of the circuit that is edited, once
    assert LabelWireIn.get_circuit_parameters(circuit)["label"]["invalid_list"] == ["clk"]
    assert LabelWireOut.get_circuit_parameters(circuit)["label"]["items"] == ["clk"]
    # Saved and loaded again
    saved = tmp_path / "top.circuit"
    circuit.to_json_file(saved)
    loaded = Circuit()
    loaded.from_json_file(str(saved))
    loaded.init()
    loaded.run(ns=100)
    values = {
        component.name(): component.y.value
        for component in loaded.get_toplevel_components()
        if isinstance(component, SubCircuit)
    }
    assert sorted(values.values()) == [0, 1]


@pytest.mark.sanity
def test_label_wire_out_of_a_subcircuit_is_not_driven_from_outside(tmp_path):
    """A LabelWireOut without a LabelWireIn in its file is undefined, like on its own"""
    path = _label_pass(tmp_path / "sink_only.circuit", sink_only=True)
    circuit = Circuit()
    _top_label(circuit, 1)
    part = SubCircuit(circuit, path)
    StaticValue(circuit, value=1).O.wire = part.a
    with pytest.warns(UserWarning, match="no LabelWireIn"):
        circuit.init()
    circuit.run(ns=100)
    assert part.y.value == "X"


@pytest.mark.sanity
def test_label_wires_of_nested_subcircuits(tmp_path):
    """The same label at each level: the top, a subcircuit and the subcircuit in it"""
    inner = _label_pass(tmp_path / "inner.circuit")
    outer = Circuit(name="outer")
    a = CircuitInput(outer, label="a")
    y = CircuitOutput(outer, label="y")
    inner_y = CircuitOutput(outer, label="inner_y")
    wire_in = LabelWireIn(outer, "clk_in", label="clk")
    a.port("a").wire = wire_in.port("clk")
    wire_out = LabelWireOut(outer, "clk_out", label="clk")
    wire_out.port("clk").wire = y.port("y")
    part = SubCircuit(outer, inner)
    StaticValue(outer, value=0).O.wire = part.a
    part.y.wire = inner_y.port("inner_y")
    path = tmp_path / "outer.circuit"
    outer.to_json_file(path)

    circuit = Circuit()
    top_out = _top_label(circuit, 0)
    sub = SubCircuit(circuit, path)
    StaticValue(circuit, value=1).O.wire = sub.a
    circuit.init()
    circuit.run(ns=100)
    assert (top_out.port("clk").value, sub.y.value, sub.inner_y.value) == (0, 1, 0)
