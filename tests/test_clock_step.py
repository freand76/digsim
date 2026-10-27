# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""Pytest module to test Step Clock, running to the next rising edge of a clock"""

from digsim.app._clock_step import step_clock
from digsim.circuit import Circuit
from digsim.circuit.components import NOT, Clock, Counter, StaticValue


def test_step_clock_counts_once():
    """Each step is one rising edge: a counter counts one, and its output has settled"""
    circuit = Circuit()
    clock = Clock(circuit, frequency=10)
    counter = Counter(circuit, width=4)
    inverter = NOT(circuit)
    clock.O.wire = counter.clk
    StaticValue(circuit, value=0).O.wire = counter.R
    counter.CO.wire = inverter.A
    circuit.init()
    for count in range(1, 5):
        assert step_clock(circuit)
        assert counter.Q.value == count
        # Just before the falling edge, half a period after the rising one
        assert circuit.time_ns == (2 * count - 1) * clock.half_period_ns + clock.half_period_ns - 1
        assert clock.O.value == 1
        assert inverter.Y.value == 1


def test_step_clock_with_two_clocks():
    """It stops before the next edge of any clock"""
    circuit = Circuit()
    slow = Clock(circuit, frequency=1)
    fast = Clock(circuit, frequency=3)
    circuit.init()
    assert step_clock(circuit)
    # The fast clock rises first, at half its period, and toggles again a period later
    assert fast.O.value == 1
    assert circuit.time_ns == 2 * fast.half_period_ns - 1
    assert slow.O.value == 0


def test_step_clock_without_clock():
    circuit = Circuit()
    StaticValue(circuit)
    circuit.init()
    assert not step_clock(circuit)
