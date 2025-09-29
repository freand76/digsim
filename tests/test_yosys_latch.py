# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Pystest module to test functionality of yosys latches"""

import pytest
from utilities import _H, _L, inv

from digsim.circuit import Circuit
from digsim.circuit.components._yosys_atoms import (
    _DLATCH_N_,
    _DLATCH_NN0_,
    _DLATCH_NN1_,
    _DLATCH_NP0_,
    _DLATCH_NP1_,
    _DLATCH_P_,
    _DLATCH_PN0_,
    _DLATCH_PN1_,
    _DLATCH_PP0_,
    _DLATCH_PP1_,
)


@pytest.mark.parametrize(
    "test_class, e_level",
    [
        (_DLATCH_N_, _L),
        (_DLATCH_P_, _H),
    ],
)
def test_yosys_dlatch_x_(test_class, e_level):
    """Test _DLATCH_X_"""
    circuit = Circuit()
    _dut = test_class(circuit, "DUT")

    # Enable Active

    _dut.E.value = e_level
    _dut.D.value = 1
    circuit.run(ms=1)
    assert _dut.Q.value == 1

    _dut.D.value = 0
    circuit.run(ms=1)
    assert _dut.Q.value == 0

    _dut.D.value = "X"
    circuit.run(ms=1)
    assert _dut.Q.value == "X"

    # Enable Inactive
    _dut.E.value = inv(e_level)
    circuit.run(ms=1)
    assert _dut.Q.value == "X"

    _dut.D.value = 1
    circuit.run(ms=1)
    assert _dut.Q.value == "X"

    _dut.D.value = 0
    circuit.run(ms=1)
    assert _dut.Q.value == "X"


@pytest.mark.parametrize(
    "test_class, e_level, r_level, r_value",
    [
        (_DLATCH_NN0_, _L, _L, _L),
        (_DLATCH_NN1_, _L, _L, _H),
        (_DLATCH_NP0_, _L, _H, _L),
        (_DLATCH_NP1_, _L, _H, _H),
        (_DLATCH_PN0_, _H, _L, _L),
        (_DLATCH_PN1_, _H, _L, _H),
        (_DLATCH_PP0_, _H, _H, _L),
        (_DLATCH_PP1_, _H, _H, _H),
    ],
)
def test_yosys_dlatch_xxx_(test_class, e_level, r_level, r_value):
    """Test _DLATCH_XXX_"""
    circuit = Circuit()
    _dut = test_class(circuit, "DUT")

    # Enable Active

    _dut.E.value = e_level
    _dut.R.value = inv(r_level)
    _dut.D.value = 1
    circuit.run(ms=1)
    assert _dut.Q.value == 1

    _dut.D.value = 0
    circuit.run(ms=1)
    assert _dut.Q.value == 0

    _dut.D.value = "X"
    circuit.run(ms=1)
    assert _dut.Q.value == "X"

    # Enable Inactive
    _dut.E.value = inv(e_level)
    circuit.run(ms=1)
    assert _dut.Q.value == "X"

    _dut.D.value = 1
    circuit.run(ms=1)
    assert _dut.Q.value == "X"

    _dut.D.value = 0
    circuit.run(ms=1)
    assert _dut.Q.value == "X"

    _dut.R.value = r_level
    circuit.run(ms=1)
    assert _dut.Q.value == r_value

    # Enable Active (but it reset)
    _dut.E.value = e_level
    _dut.D.value = 1
    circuit.run(ms=1)
    assert _dut.Q.value == r_value
