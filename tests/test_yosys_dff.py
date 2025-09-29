# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Pystest module to test functionality of yosys dff"""

import pytest
from utilities import _H, _L, inv

from digsim.circuit import Circuit
from digsim.circuit.components._yosys_atoms import (
    _DFF_N_,
    _DFF_NN0_,
    _DFF_NN1_,
    _DFF_NP0_,
    _DFF_NP1_,
    _DFF_P_,
    _DFF_PN0_,
    _DFF_PN1_,
    _DFF_PP0_,
    _DFF_PP1_,
    _DFFE_NN0N_,
    _DFFE_NN0P_,
    _DFFE_NN1N_,
    _DFFE_NN1P_,
    _DFFE_NN_,
    _DFFE_NP0N_,
    _DFFE_NP0P_,
    _DFFE_NP1N_,
    _DFFE_NP1P_,
    _DFFE_NP_,
    _DFFE_PN0N_,
    _DFFE_PN0P_,
    _DFFE_PN1N_,
    _DFFE_PN1P_,
    _DFFE_PN_,
    _DFFE_PP0N_,
    _DFFE_PP0P_,
    _DFFE_PP1N_,
    _DFFE_PP1P_,
    _DFFE_PP_,
)


@pytest.mark.parametrize(
    "test_class, c_edge",
    [
        (_DFF_N_, _L),
        (_DFF_P_, _H),
    ],
)
def test_yosys_dff_x_(test_class, c_edge):
    """Test _DFF_X_"""
    circuit = Circuit()
    _dut = test_class(circuit, "DUT")

    # Start before clock edge
    _dut.C.value = inv(c_edge)
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


@pytest.mark.parametrize(
    "test_class, c_edge, r_level, r_value",
    [
        (_DFF_NN0_, _L, _L, _L),
        (_DFF_NN1_, _L, _L, _H),
        (_DFF_NP0_, _L, _H, _L),
        (_DFF_NP1_, _L, _H, _H),
        (_DFF_PN0_, _H, _L, _L),
        (_DFF_PN1_, _H, _L, _H),
        (_DFF_PP0_, _H, _H, _L),
        (_DFF_PP1_, _H, _H, _H),
    ],
)
def test_yosys_dff_xxx_(test_class, c_edge, r_level, r_value):
    """Test _DFF_XXX_"""
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

    # Test asynchronous reset
    _dut.R.value = r_level
    circuit.run(ms=1)
    assert _dut.Q.value == r_value


@pytest.mark.parametrize(
    "test_class, c_edge, e_level",
    [
        (_DFFE_NN_, _L, _L),
        (_DFFE_NP_, _L, _H),
        (_DFFE_PN_, _H, _L),
        (_DFFE_PP_, _H, _H),
    ],
)
def test_yosys_dffe_xx_(test_class, c_edge, e_level):
    """Test _DFFE_XX_"""
    circuit = Circuit()
    _dut = test_class(circuit, "DUT")

    # Clock Enable = 1
    _dut.E.value = e_level

    # Start before clock edge
    _dut.E.value = e_level
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


@pytest.mark.parametrize(
    "test_class, c_edge, r_level, r_value, e_level",
    [
        (_DFFE_NN0N_, _L, _L, _L, _L),
        (_DFFE_NN0P_, _L, _L, _L, _H),
        (_DFFE_NN1N_, _L, _L, _H, _L),
        (_DFFE_NN1P_, _L, _L, _H, _H),
        (_DFFE_NP0N_, _L, _H, _L, _L),
        (_DFFE_NP0P_, _L, _H, _L, _H),
        (_DFFE_NP1N_, _L, _H, _H, _L),
        (_DFFE_NP1P_, _L, _H, _H, _H),
        (_DFFE_PN0N_, _H, _L, _L, _L),
        (_DFFE_PN0P_, _H, _L, _L, _H),
        (_DFFE_PN1N_, _H, _L, _H, _L),
        (_DFFE_PN1P_, _H, _L, _H, _H),
        (_DFFE_PP0N_, _H, _H, _L, _L),
        (_DFFE_PP0P_, _H, _H, _L, _H),
        (_DFFE_PP1N_, _H, _H, _H, _L),
        (_DFFE_PP1P_, _H, _H, _H, _H),
    ],
)
def test_yosys_dffe_xxxx_(test_class, c_edge, r_level, r_value, e_level):
    """Test _DFFE_XXXX_"""
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

    # Test asynchronous reset
    _dut.R.value = r_level
    circuit.run(ms=1)
    assert _dut.Q.value == r_value
