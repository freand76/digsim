# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""
Step Clock: run the simulation to the next rising edge of a clock (kept free from Qt
imports so that it can be tested without a display)
"""

from __future__ import annotations

import time

from digsim.circuit import Circuit
from digsim.circuit.components import Clock
from digsim.circuit.components.atoms import DigsimException


# How far the simulation runs at most to find a clock edge (a 1 Hz clock has one a second)
MAX_STEP_NS = 2_000_000_000
# The events between the looks at the clock, while it looks for an edge
_EVENTS_PER_LOOK = 1000


class StepTooSlow(DigsimException):
    """Step Clock took longer than its time limit, like for a circuit that oscillates"""


def circuit_clocks(circuit: Circuit) -> list[Clock]:
    """The clocks of a circuit"""
    return [
        component
        for component in circuit.get_toplevel_components()
        if isinstance(component, Clock)
    ]


def step_clock(circuit: Circuit, max_seconds: float | None = None) -> bool:
    """
    Run to the next rising edge of a clock, and on until just before the next edge of a
    clock, so that the logic after the edge has settled. Returns False, and runs at most
    MAX_STEP_NS, if no clock has a rising edge (there is no clock). Raises StepTooSlow if
    it takes more than 'max_seconds' on the clock: the circuit is where it got to.
    """
    deadline = None if max_seconds is None else time.perf_counter() + max_seconds
    clocks = circuit_clocks(circuit)
    limit = circuit.time_ns + MAX_STEP_NS
    levels = [clock.O.value for clock in clocks]
    events = 0
    while True:
        events += 1
        if (
            deadline is not None
            and events % _EVENTS_PER_LOOK == 0
            and time.perf_counter() > deadline
        ):
            raise StepTooSlow("Step Clock took too long, the circuit is slow")
        processed, _ = circuit.process_single_event(stop_time_ns=limit)
        if not processed:
            circuit.run_until(ns=limit)
            return False
        new_levels = [clock.O.value for clock in clocks]
        rising = [
            clock
            for clock, old, new in zip(clocks, levels, new_levels, strict=True)
            if old == 0 and new == 1
        ]
        if rising:
            break
        levels = new_levels
    next_edge = min(_next_edge(clock, circuit.time_ns) for clock in clocks)
    if deadline is None:
        circuit.run(ns=next_edge - 1 - circuit.time_ns)
    elif not circuit.run_within(
        max(0.0, deadline - time.perf_counter()), ns=next_edge - 1 - circuit.time_ns
    ).complete:
        raise StepTooSlow("Step Clock took too long, the circuit is slow")
    return True


def _next_edge(clock: Clock, time_ns: int) -> int:
    """When a clock toggles next after a time: every half period from time 0"""
    half_period = clock.half_period_ns
    return (time_ns // half_period + 1) * half_period
