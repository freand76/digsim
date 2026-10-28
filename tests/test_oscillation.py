# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""Pytest module to test runs with a time limit, and finding the ports that oscillate"""

import time

from digsim.circuit import Circuit
from digsim.circuit.components import AND, NAND, NOT, Clock, OnOffSwitch


def _ring(circuit):
    """A ring oscillator, a NAND and two NOT gates, that runs while EN is on"""
    enable = OnOffSwitch(circuit, "EN")
    gate, first, second = NAND(circuit, "g"), NOT(circuit, "n1"), NOT(circuit, "n2")
    enable.O.wire = gate.A
    gate.Y.wire = first.A
    first.Y.wire = second.A
    second.Y.wire = gate.B
    return enable, gate, first, second


def _values(circuit, ports, ns):
    """The values of ports after each nanosecond"""
    values = []
    for _ in range(ns):
        circuit.run(ns=1)
        values.append(tuple(port.value for port in ports))
    return values


def test_run_within_stops_an_oscillation_in_time():
    circuit = Circuit()
    enable, *_ = _ring(circuit)
    circuit.init()
    # Defined first, with the enable off, a ring that starts at X stays X
    circuit.run(ns=20)
    enable.turn_on()
    start = time.perf_counter()
    result = circuit.run_within(0.2, ms=50)
    assert time.perf_counter() - start < 2
    assert not result.complete
    assert circuit.time_ns < 50_000_000


def test_run_within_runs_all_of_a_quiet_circuit():
    circuit = Circuit()
    Clock(circuit, frequency=1000)
    circuit.init()
    result = circuit.run_within(1, ms=50)
    assert result.complete
    assert circuit.time_ns == 50_000_000


def test_run_within_has_the_events_of_one_run():
    """Stopped and continued, the oscillation is the same as in one long run"""
    runs = []
    for within in (False, True):
        circuit = Circuit()
        enable, gate, first, second = _ring(circuit)
        circuit.init()
        circuit.run(ns=20)
        enable.turn_on()
        if within:
            while circuit.time_ns < 20 + 30_000:
                circuit.run_within(0.001, ns=20 + 30_000 - circuit.time_ns)
        else:
            circuit.run(ns=30_000)
        runs.append((circuit.time_ns, _values(circuit, [gate.Y, first.Y, second.Y], 50)))
    assert runs[0] == runs[1]


def test_oscillating_ports():
    circuit = Circuit()
    enable, gate, first, second = _ring(circuit)
    quiet = AND(circuit, "quiet")
    enable.O.wire = quiet.A
    circuit.init()
    circuit.run(ns=20)
    enable.turn_on()
    circuit.run(ns=100)
    found = circuit.oscillating_ports()
    assert set(found) == {gate.Y, first.Y, second.Y}
    # Off, it stops
    enable.turn_off()
    circuit.run(ns=100)
    assert circuit.oscillating_ports() == []


def test_a_clock_does_not_oscillate():
    circuit = Circuit()
    Clock(circuit, frequency=1_000_000)
    circuit.init()
    assert circuit.oscillating_ports() == []


def test_oscillating_ports_within_a_time():
    """Out of time it stops, with what it counted: here nothing yet"""
    circuit = Circuit()
    enable, _, _, _ = _ring(circuit)
    circuit.init()
    circuit.run(ns=20)
    enable.turn_on()
    circuit.run(ns=100)
    before = circuit.time_ns
    assert circuit.oscillating_ports(max_seconds=0) == []
    assert circuit.time_ns == before
    assert circuit.oscillating_ports(max_seconds=10)
