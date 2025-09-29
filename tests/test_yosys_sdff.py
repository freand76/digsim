# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Pystest module to test functionality of yosys synrhonous reset dff"""

import pytest
from utilities import _H, _L, inv

from digsim.circuit import Circuit
from digsim.circuit.components._yosys_atoms import (
    _SDFF_NN0_,
    _SDFF_NN1_,
    _SDFF_NP0_,
    _SDFF_NP1_,
    _SDFF_PN0_,
    _SDFF_PN1_,
    _SDFF_PP0_,
    _SDFF_PP1_,
    _SDFFCE_NN0N_,
    _SDFFCE_NN0P_,
    _SDFFCE_NN1N_,
    _SDFFCE_NN1P_,
    _SDFFCE_NP0N_,
    _SDFFCE_NP0P_,
    _SDFFCE_NP1N_,
    _SDFFCE_NP1P_,
    _SDFFCE_PN0N_,
    _SDFFCE_PN0P_,
    _SDFFCE_PN1N_,
    _SDFFCE_PN1P_,
    _SDFFCE_PP0N_,
    _SDFFCE_PP0P_,
    _SDFFCE_PP1N_,
    _SDFFCE_PP1P_,
    _SDFFE_NN0N_,
    _SDFFE_NN0P_,
    _SDFFE_NN1N_,
    _SDFFE_NN1P_,
    _SDFFE_NP0N_,
    _SDFFE_NP0P_,
    _SDFFE_NP1N_,
    _SDFFE_NP1P_,
    _SDFFE_PN0N_,
    _SDFFE_PN0P_,
    _SDFFE_PN1N_,
    _SDFFE_PN1P_,
    _SDFFE_PP0N_,
    _SDFFE_PP0P_,
    _SDFFE_PP1N_,
    _SDFFE_PP1P_,
)


@pytest.mark.parametrize(
    "test_class, c_edge, r_level, r_value",
    [
        (_SDFF_NN0_, _L, _L, _L),
        (_SDFF_NN1_, _L, _L, _H),
        (_SDFF_NP0_, _L, _H, _L),
        (_SDFF_NP1_, _L, _H, _H),
        (_SDFF_PN0_, _H, _L, _L),
        (_SDFF_PN1_, _H, _L, _H),
        (_SDFF_PP0_, _H, _H, _L),
        (_SDFF_PP1_, _H, _H, _H),
    ],
)
def test_yosys_sdff_xxx_(test_class, c_edge, r_level, r_value):
    """Test _SDFF_XXX_"""
    circuit = Circuit()
    _dut = test_class(circuit, "DUT")

    # Start before clock edge
    _dut.C.value = inv(c_edge)
    _dut.R.value = inv(r_level)
    _dut.D.value = 0
    # assert _dut.Q.value == "X"
    circuit.run(ms=1)
    # assert _dut.Q.value == "X"

    _dut.C.value = c_edge
    circuit.run(ms=1)
    assert _dut.Q.value == 0

    _dut.D.value = 1
    _dut.C.value = inv(c_edge)
    circuit.run(ms=1)
    assert _dut.Q.value == 0

    _dut.C.value = c_edge
    circuit.run(ms=1)
    assert _dut.Q.value == 1

    # Test synchronous reset
    _dut.R.value = r_level
    circuit.run(ms=1)
    assert _dut.Q.value == 1

    _dut.C.value = inv(c_edge)
    circuit.run(ms=1)
    assert _dut.Q.value == 1

    # Synchronous reset will triger on clock edge
    _dut.C.value = c_edge
    circuit.run(ms=1)
    assert _dut.Q.value == r_value


@pytest.mark.parametrize(
    "test_class, c_edge, r_level, r_value, e_level",
    [
        (_SDFFE_NN0N_, _L, _L, _L, _L),
        (_SDFFE_NN0P_, _L, _L, _L, _H),
        (_SDFFE_NN1N_, _L, _L, _H, _L),
        (_SDFFE_NN1P_, _L, _L, _H, _H),
        (_SDFFE_NP0N_, _L, _H, _L, _L),
        (_SDFFE_NP0P_, _L, _H, _L, _H),
        (_SDFFE_NP1N_, _L, _H, _H, _L),
        (_SDFFE_NP1P_, _L, _H, _H, _H),
        (_SDFFE_PN0N_, _H, _L, _L, _L),
        (_SDFFE_PN0P_, _H, _L, _L, _H),
        (_SDFFE_PN1N_, _H, _L, _H, _L),
        (_SDFFE_PN1P_, _H, _L, _H, _H),
        (_SDFFE_PP0N_, _H, _H, _L, _L),
        (_SDFFE_PP0P_, _H, _H, _L, _H),
        (_SDFFE_PP1N_, _H, _H, _H, _L),
        (_SDFFE_PP1P_, _H, _H, _H, _H),
    ],
)
def test_yosys_sdffe_xxxx_(test_class, c_edge, r_level, r_value, e_level):
    """Test _SDFFE_XXXX_"""
    circuit = Circuit()
    _dut = test_class(circuit, "DUT")

    # Clock Enable = 1
    _dut.E.value = e_level

    # Start before clock edge
    _dut.C.value = inv(c_edge)
    _dut.R.value = inv(r_level)
    _dut.D.value = 0
    # assert _dut.Q.value == "X"
    circuit.run(ms=1)
    # assert _dut.Q.value == "X"

    _dut.C.value = c_edge
    circuit.run(ms=1)
    assert _dut.Q.value == 0

    _dut.D.value = 1
    _dut.C.value = inv(c_edge)
    circuit.run(ms=1)
    assert _dut.Q.value == 0

    _dut.C.value = c_edge
    circuit.run(ms=1)
    assert _dut.Q.value == 1

    # Clock Enable = 0
    _dut.E.value = inv(e_level)

    _dut.D.value = 0
    _dut.C.value = inv(c_edge)
    circuit.run(ms=1)
    assert _dut.Q.value == 1

    _dut.C.value = c_edge
    circuit.run(ms=1)
    assert _dut.Q.value == 1

    # Test synchronous reset
    _dut.R.value = r_level
    circuit.run(ms=1)
    assert _dut.Q.value == 1

    _dut.C.value = inv(c_edge)
    circuit.run(ms=1)
    assert _dut.Q.value == 1

    # Synchronous reset will triger on clock edge
    _dut.C.value = c_edge
    circuit.run(ms=1)
    assert _dut.Q.value == r_value


@pytest.mark.parametrize(
    "test_class, c_edge, r_level, r_value, e_level",
    [
        (_SDFFCE_NN0N_, _L, _L, _L, _L),
        (_SDFFCE_NN0P_, _L, _L, _L, _H),
        (_SDFFCE_NN1N_, _L, _L, _H, _L),
        (_SDFFCE_NN1P_, _L, _L, _H, _H),
        (_SDFFCE_NP0N_, _L, _H, _L, _L),
        (_SDFFCE_NP0P_, _L, _H, _L, _H),
        (_SDFFCE_NP1N_, _L, _H, _H, _L),
        (_SDFFCE_NP1P_, _L, _H, _H, _H),
        (_SDFFCE_PN0N_, _H, _L, _L, _L),
        (_SDFFCE_PN0P_, _H, _L, _L, _H),
        (_SDFFCE_PN1N_, _H, _L, _H, _L),
        (_SDFFCE_PN1P_, _H, _L, _H, _H),
        (_SDFFCE_PP0N_, _H, _H, _L, _L),
        (_SDFFCE_PP0P_, _H, _H, _L, _H),
        (_SDFFCE_PP1N_, _H, _H, _H, _L),
        (_SDFFCE_PP1P_, _H, _H, _H, _H),
    ],
)
def test_yosys_sdffce_xxxx_(test_class, c_edge, r_level, r_value, e_level):
    """Test _SDFFCE_XXXX_"""
    circuit = Circuit()
    _dut = test_class(circuit, "DUT")

    # Clock Enable = 1
    _dut.E.value = e_level

    # Start before clock edge
    _dut.C.value = inv(c_edge)
    _dut.R.value = inv(r_level)
    _dut.D.value = 0
    # assert _dut.Q.value == "X"
    circuit.run(ms=1)
    # assert _dut.Q.value == "X"

    _dut.C.value = c_edge
    circuit.run(ms=1)
    assert _dut.Q.value == 0

    _dut.D.value = 1
    _dut.C.value = inv(c_edge)
    circuit.run(ms=1)
    assert _dut.Q.value == 0

    _dut.C.value = c_edge
    circuit.run(ms=1)
    assert _dut.Q.value == 1

    # Clock Enable = 0
    _dut.E.value = inv(e_level)

    _dut.D.value = 0
    _dut.C.value = inv(c_edge)
    circuit.run(ms=1)
    assert _dut.Q.value == 1

    _dut.C.value = c_edge
    circuit.run(ms=1)
    assert _dut.Q.value == 1

    # Test synchronous reset (clock enable = 0)
    _dut.R.value = r_level
    circuit.run(ms=1)
    assert _dut.Q.value == 1

    _dut.C.value = inv(c_edge)
    circuit.run(ms=1)
    assert _dut.Q.value == 1

    # Synchronous reset has no affect when clock enable = 0
    _dut.C.value = c_edge
    circuit.run(ms=1)
    assert _dut.Q.value == 1

    # Clock Enable = 1
    _dut.E.value = e_level
    circuit.run(ms=1)
    assert _dut.Q.value == 1

    _dut.C.value = inv(c_edge)
    circuit.run(ms=1)
    assert _dut.Q.value == 1

    # Synchronous reset is applied for clock enable = 1
    _dut.C.value = c_edge
    circuit.run(ms=1)
    assert _dut.Q.value == r_value
