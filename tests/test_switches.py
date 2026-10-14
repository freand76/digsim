# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Pytest module to test the switch components"""

from digsim.circuit import Circuit
from digsim.circuit.components import DipSwitch, OnOffSwitch


def test_on_off_switch():
    """The switch output follows turn_on, turn_off and toggle"""
    circuit = Circuit()
    switch = OnOffSwitch(circuit)
    circuit.init()
    assert switch.O.value == 0
    assert not switch.active
    switch.turn_on()
    circuit.run(ms=1)
    assert switch.O.value == 1
    assert switch.active
    switch.toggle()
    circuit.run(ms=1)
    assert switch.O.value == 0
    switch.toggle()
    circuit.run(ms=1)
    assert switch.O.value == 1
    switch.turn_off()
    circuit.run(ms=1)
    assert switch.O.value == 0
    assert not switch.active


def test_on_off_switch_init_turns_off():
    """Initializing the circuit turns the switch off"""
    circuit = Circuit()
    switch = OnOffSwitch(circuit)
    circuit.init()
    switch.turn_on()
    circuit.run(ms=1)
    circuit.init()
    assert switch.O.value == 0
    assert not switch.active


def test_dip_switch():
    """Toggling a selected bit changes only that output"""
    circuit = Circuit()
    switch = DipSwitch(circuit, bits=4)
    circuit.init()
    switch.select(2)
    switch.toggle()
    assert [switch.is_set(bit) for bit in range(4)] == [False, False, True, False]
    switch.toggle()
    assert not switch.is_set(2)
    switch.select(None)
    switch.toggle()
    assert not any(switch.is_set(bit) for bit in range(4))
