# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""Pytest module to test the circuit ports, the interface of a circuit"""

import pytest

from digsim.circuit import Circuit
from digsim.circuit.components import (
    CircuitInOut,
    CircuitInput,
    CircuitOutput,
    StaticValue,
    TristateBuffer,
)
from digsim.circuit.components.atoms import ComponentException


def test_input_to_output():
    """An input drives its value, 0 at the start, and an output shows it"""
    circuit = Circuit()
    a = CircuitInput(circuit, label="a", width=4)
    y = CircuitOutput(circuit, label="y", width=4)
    a.port("a").wire = y.port("y")
    circuit.init()
    circuit.run(ns=10)
    assert y.value == 0
    a.set_value(9)
    circuit.run(ns=10)
    assert y.value == 9
    with pytest.raises(ComponentException):
        a.set_value(16)


def test_one_bit_input_toggles():
    circuit = Circuit()
    a = CircuitInput(circuit, label="a")
    circuit.init()
    assert a.has_action
    a.onpress()
    assert a.value == 1
    a.onpress()
    assert a.value == 0
    assert not CircuitInput(circuit, label="b", width=2).has_action


def test_inout_drives_and_reads():
    """An inout port drives nothing at the start, a value when set, and reads the wire"""
    circuit = Circuit()
    io = CircuitInOut(circuit, label="io", width=4)
    other = TristateBuffer(circuit, width=4)
    data = StaticValue(circuit, width=4, value=6)
    enable = StaticValue(circuit, value=0)
    data.O.wire = other.A
    enable.O.wire = other.OE
    other.Y.wire = io.port("io")
    circuit.init()
    circuit.run(ns=10)
    assert (io.drive, io.value) == ("Z", "Z")
    io.set_value(3)
    circuit.run(ns=10)
    assert io.value == 3
    io.set_value("Z")
    enable.parameter_set("value", 1)
    enable.reconfigure()
    circuit.run(ns=10)
    assert io.value == 6


def test_labels_are_unique_names():
    circuit = Circuit()
    CircuitInput(circuit, label="a")
    with pytest.raises(ComponentException, match="has a port 'a'"):
        CircuitOutput(circuit, label="a")
    with pytest.raises(ComponentException, match="not a name"):
        CircuitInput(circuit, label="1x")
    # A new port gets a free name in the settings dialog
    assert CircuitInput.get_circuit_parameters(circuit)["label"]["default"] == "in"
    CircuitInput(circuit, label="in")
    assert CircuitInput.get_circuit_parameters(circuit)["label"]["default"] == "in2"


def test_circuit_ports():
    """Circuit.ports() lists the circuit ports, the interface of the circuit"""
    circuit = Circuit()
    CircuitInput(circuit, label="a", width=2)
    StaticValue(circuit)
    CircuitOutput(circuit, label="y")
    CircuitInOut(circuit, label="bus", width=8)
    assert [(p.label(), p.DIRECTION, p.width) for p in circuit.ports()] == [
        ("a", "in", 2),
        ("y", "out", 1),
        ("bus", "inout", 8),
    ]
