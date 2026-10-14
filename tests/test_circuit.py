# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Pytest module to test the Circuit class"""

from digsim.circuit import Circuit
from digsim.circuit.components import AND, SR, Led, PushButton, YosysComponent


def test_delete_component():
    """A deleted component is removed from the circuit and disconnected"""
    circuit = Circuit()
    button = PushButton(circuit, "button")
    gate = AND(circuit, "gate")
    button.O.wire = gate.A
    circuit.delete_component(gate)
    assert [component.name() for component in circuit.components] == ["button"]
    assert button.O.wired_ports == []


def test_delete_multi_component():
    """Deleting a component built from other components removes them too"""
    circuit = Circuit()
    latch = SR(circuit, "latch")
    led = Led(circuit, "led")
    latch.Q.wire = led.I
    assert len(circuit.components) == 4  # the latch, its two NOR gates and the LED
    circuit.delete_component(latch)
    assert [component.name() for component in circuit.components] == ["led"]


def test_delete_yosys_component():
    """Deleting a Yosys component removes all its gates"""
    circuit = Circuit()
    counter = YosysComponent(circuit, path="examples/yosys_counter/counter.json")
    Led(circuit, "led")
    assert len(circuit.components) > 2
    circuit.delete_component(counter)
    assert [component.name() for component in circuit.components] == ["led"]
