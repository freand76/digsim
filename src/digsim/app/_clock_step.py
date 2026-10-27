# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""
Step Clock: run the simulation to the next rising edge of a clock (kept free from Qt
imports so that it can be tested without a display)
"""

from __future__ import annotations

from digsim.circuit import Circuit
from digsim.circuit.components import Clock


# How far the simulation runs at most to find a clock edge (a 1 Hz clock has one a second)
MAX_STEP_NS = 2_000_000_000


def circuit_clocks(circuit: Circuit) -> list[Clock]:
    """The clocks of a circuit"""
    return [
        component
        for component in circuit.get_toplevel_components()
        if isinstance(component, Clock)
    ]


def step_clock(circuit: Circuit) -> bool:
    """
    Run to the next rising edge of a clock, and on until just before the next edge of a
    clock, so that the logic after the edge has settled. Returns False, and runs at most
    MAX_STEP_NS, if no clock has a rising edge (there is no clock).
    """
    clocks = circuit_clocks(circuit)
    limit = circuit.time_ns + MAX_STEP_NS
    levels = [clock.O.value for clock in clocks]
    while True:
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
    circuit.run(ns=next_edge - 1 - circuit.time_ns)
    return True


def _next_edge(clock: Clock, time_ns: int) -> int:
    """When a clock toggles next after a time: every half period from time 0"""
    half_period = clock.half_period_ns
    return (time_ns // half_period + 1) * half_period
