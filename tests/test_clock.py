# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""Pytest module to test the Clock component, and running a circuit by its edges"""

import pytest

from digsim.circuit import Circuit
from digsim.circuit.components import Clock, Counter, StaticValue
from digsim.circuit.components.atoms import DigsimException


def _counter(frequency=1000):
    circuit = Circuit()
    clock = Clock(circuit, frequency=frequency)
    counter = Counter(circuit, width=4)
    clock.O.wire = counter.clk
    StaticValue(circuit, value=0).O.wire = counter.R
    circuit.init()
    return circuit, clock, counter


def test_clock_starts_low_and_rises_after_half_a_period():
    _, clock, _ = _counter()
    assert clock.O.value == 0
    assert clock.next_edge_ns(rising=True) == clock.half_period_ns
    assert clock.next_edge_ns(rising=False) == 2 * clock.half_period_ns


def test_run_until_rising_edge():
    """Each rising edge counts once, and the run stops just before the falling edge"""
    circuit, clock, counter = _counter()
    half = clock.half_period_ns
    for count in range(1, 6):
        circuit.run_until_edge(rising=clock)
        assert clock.O.value == 1
        assert counter.Q.value == count
        assert circuit.time_ns == (2 * count) * half - 1
        assert clock.next_edge_ns(rising=False) == circuit.time_ns + 1


def test_run_until_falling_edge():
    """A falling edge doesn't count, the run stops just before the rising edge"""
    circuit, clock, counter = _counter()
    half = clock.half_period_ns
    circuit.run_until_edge(falling=clock)
    assert clock.O.value == 0
    assert counter.Q.value == 1  # Through the rising edge before it
    assert circuit.time_ns == 3 * half - 1
    circuit.run_until_edge(falling=clock)
    assert counter.Q.value == 2
    assert circuit.time_ns == 5 * half - 1


def test_edges_after_a_run():
    """The next edges after a run that ended between them"""
    circuit, clock, counter = _counter()
    half = clock.half_period_ns
    circuit.run(ns=half + half // 2)
    assert clock.O.value == 1
    assert clock.next_edge_ns(rising=False) == 2 * half
    assert clock.next_edge_ns(rising=True) == 3 * half
    circuit.run_until_edge(rising=clock)
    assert counter.Q.value == 2


def test_new_frequency():
    """A new frequency changes the half periods after the next edge"""
    circuit, clock, counter = _counter(frequency=1000)
    circuit.run_until_edge(rising=clock)
    clock.parameter_set("frequency", 2000)
    clock.reconfigure()
    first = clock.next_edge_ns(rising=False)
    circuit.run_until_edge(falling=clock)
    circuit.run_until_edge(rising=clock)
    assert counter.Q.value == 2
    assert circuit.time_ns == first + 2 * clock.half_period_ns - 1


def test_clock_needs_init():
    circuit = Circuit()
    clock = Clock(circuit)
    with pytest.raises(DigsimException):
        circuit.run_until_edge(rising=clock)


def test_rising_or_falling():
    circuit, clock, _ = _counter()
    with pytest.raises(DigsimException):
        circuit.run_until_edge()
    with pytest.raises(DigsimException):
        circuit.run_until_edge(rising=clock, falling=clock)


def test_edge_of_the_clock_output():
    """The output port of a clock is the clock"""
    circuit, clock, counter = _counter()
    assert circuit.run_until_edge(rising=clock.O)
    assert circuit.time_ns == 2 * clock.half_period_ns - 1
    assert counter.Q.value == 1


def test_edge_of_a_port():
    """Another port: the run stops at the time of its edge"""
    circuit, clock, counter = _counter()
    half = clock.half_period_ns
    assert circuit.run_until_edge(rising=counter.clk)
    assert circuit.time_ns == half
    assert circuit.run_until_edge(falling=counter.clk)
    assert circuit.time_ns == 2 * half
    # The counter counted at the rising edge
    assert counter.Q.value == 1


def test_port_without_an_edge():
    """A port that doesn't change: the run stops after max_ns"""
    circuit = Circuit()
    value = StaticValue(circuit, value=1)
    circuit.init()
    assert not circuit.run_until_edge(rising=value.O, max_ns=1000)
    assert circuit.time_ns == 1000


def test_clock_runs_on_after_a_new_wire():
    """The native engine runs the clock, a new wire hands it to Python: it goes on"""
    circuit, clock, counter = _counter()
    for count in range(1, 4):
        circuit.run_until_edge(rising=clock)
        assert counter.Q.value == count
    probe = Counter(circuit, width=4)
    clock.O.wire = probe.clk
    for count in range(4, 8):
        circuit.run_until_edge(rising=clock)
        assert counter.Q.value == count
    assert circuit.time_ns == 14 * clock.half_period_ns - 1
