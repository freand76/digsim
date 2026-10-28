# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""Pytest module to test the flip-flop components"""

import pytest

from digsim.circuit import Circuit
from digsim.circuit.components import SRFF, ClockedJKFF, ClockedSRFF, ClockedTFF


# Also on the other platforms: the minimal scope of the tests (see .github/workflows)
pytestmark = pytest.mark.sanity


def _clock(circuit, flip_flop):
    flip_flop.C.value = 1
    circuit.run(ms=1)
    flip_flop.C.value = 0
    circuit.run(ms=1)


def test_srff():
    """S sets and R resets the output, without a clock"""
    circuit = Circuit()
    flip_flop = SRFF(circuit)
    circuit.init()
    flip_flop.S.value = 1
    circuit.run(ms=1)
    assert flip_flop.Q.value == 1
    flip_flop.S.value = 0
    flip_flop.R.value = 1
    circuit.run(ms=1)
    assert flip_flop.Q.value == 0


def test_clocked_srff():
    """S and R only take effect on a rising clock edge"""
    circuit = Circuit()
    flip_flop = ClockedSRFF(circuit)
    circuit.init()
    flip_flop.C.value = 0
    flip_flop.S.value = 1
    flip_flop.R.value = 0
    circuit.run(ms=1)
    assert flip_flop.Q.value == "X"
    _clock(circuit, flip_flop)
    assert flip_flop.Q.value == 1
    flip_flop.S.value = 0
    flip_flop.R.value = 1
    _clock(circuit, flip_flop)
    assert flip_flop.Q.value == 0


def test_clocked_jkff():
    """J sets, K resets and J and K together toggle the output"""
    circuit = Circuit()
    flip_flop = ClockedJKFF(circuit)
    circuit.init()
    flip_flop.C.value = 0
    for j, k, expected in [(1, 0, 1), (0, 1, 0), (1, 1, 1), (1, 1, 0), (0, 0, 0)]:
        flip_flop.J.value = j
        flip_flop.K.value = k
        _clock(circuit, flip_flop)
        assert flip_flop.Q.value == expected


def test_clocked_jkff_undefined_k():
    """An undefined K doesn't toggle the output"""
    circuit = Circuit()
    flip_flop = ClockedJKFF(circuit)
    circuit.init()
    flip_flop.C.value = 0
    flip_flop.J.value = 1
    flip_flop.K.value = 0
    _clock(circuit, flip_flop)
    assert flip_flop.Q.value == 1
    flip_flop.K.value = "X"
    _clock(circuit, flip_flop)
    assert flip_flop.Q.value == 1


def test_clocked_tff():
    """T toggles the output on a rising clock edge"""
    circuit = Circuit()
    flip_flop = ClockedTFF(circuit)
    circuit.init()
    flip_flop.C.value = 0
    _clock(circuit, flip_flop)
    assert flip_flop.Q.value == "X"
    flip_flop.T.value = 1
    for expected in [0, 1, 0]:
        _clock(circuit, flip_flop)
        assert flip_flop.Q.value == expected


def test_clocked_tff_reinit():
    """Initializing the circuit again resets the output"""
    circuit = Circuit()
    flip_flop = ClockedTFF(circuit)
    circuit.init()
    flip_flop.C.value = 0
    flip_flop.T.value = 1
    _clock(circuit, flip_flop)
    assert flip_flop.Q.value == 0
    circuit.init()
    assert flip_flop.Q.value == "X"
