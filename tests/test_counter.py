# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""Pytest module to test the counter"""

from digsim.circuit import Circuit
from digsim.circuit.components import Counter


def _clock(circuit, counter):
    counter.clk.value = 1
    circuit.run(ns=10)
    counter.clk.value = 0
    circuit.run(ns=10)


def _counter(**settings):
    circuit = Circuit()
    counter = Counter(circuit, **settings)
    circuit.init()
    counter.clk.value = 0
    counter.R.value = 0
    circuit.run(ns=10)
    return circuit, counter


def test_counter_counts_and_wraps():
    """It starts at 0, counts up on each rising edge, and the carry is 1 at the top"""
    circuit, counter = _counter(width=2)
    assert counter.Q.value == 0
    values = []
    for _ in range(4):
        _clock(circuit, counter)
        values.append((counter.Q.value, counter.CO.value))
    assert values == [(1, 0), (2, 0), (3, 1), (0, 0)]


def test_counter_reset():
    """R sets Q to 0 at once, without a clock edge"""
    circuit, counter = _counter(width=4)
    _clock(circuit, counter)
    _clock(circuit, counter)
    counter.R.value = 1
    circuit.run(ns=10)
    assert counter.Q.value == 0
    _clock(circuit, counter)
    assert counter.Q.value == 0


def test_counter_down_enable_and_load():
    circuit, counter = _counter(width=4, enable=True, up_down=True, load=True)
    counter.EN.value = 1
    counter.UP.value = 0
    counter.LD.value = 0
    circuit.run(ns=10)
    # Down from 0 wraps to 15, the carry is 1 at 0 counting down
    assert counter.CO.value == 1
    _clock(circuit, counter)
    assert counter.Q.value == 15
    counter.EN.value = 0
    _clock(circuit, counter)
    assert counter.Q.value == 15
    counter.EN.value = 1
    counter.LD.value = 1
    counter.D.value = 9
    _clock(circuit, counter)
    assert counter.Q.value == 9
