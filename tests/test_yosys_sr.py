# Copyright (c) Fredrik Andersson, 2023-2024
# All rights reserved

"""Pystest module to test functionality of yosys sr"""

import pytest
from utilities import _H, _L, inv

from digsim.circuit import Circuit
from digsim.circuit.components._yosys_atoms import (
    _DFFSR_NNN_,
    _DFFSR_NNP_,
    _DFFSR_NPN_,
    _DFFSR_NPP_,
    _DFFSR_PNN_,
    _DFFSR_PNP_,
    _DFFSR_PPN_,
    _DFFSR_PPP_,
    _DFFSRE_NNNN_,
    _DFFSRE_NNNP_,
    _DFFSRE_NNPN_,
    _DFFSRE_NNPP_,
    _DFFSRE_NPNN_,
    _DFFSRE_NPNP_,
    _DFFSRE_NPPN_,
    _DFFSRE_NPPP_,
    _DFFSRE_PNNN_,
    _DFFSRE_PNNP_,
    _DFFSRE_PNPN_,
    _DFFSRE_PNPP_,
    _DFFSRE_PPNN_,
    _DFFSRE_PPNP_,
    _DFFSRE_PPPN_,
    _DFFSRE_PPPP_,
    _DLATCHSR_NNN_,
    _DLATCHSR_NNP_,
    _DLATCHSR_NPN_,
    _DLATCHSR_NPP_,
    _DLATCHSR_PNN_,
    _DLATCHSR_PNP_,
    _DLATCHSR_PPN_,
    _DLATCHSR_PPP_,
    _SR_NN_,
    _SR_NP_,
    _SR_PN_,
    _SR_PP_,
)


@pytest.mark.parametrize(
    "test_class,s_level,r_level",
    [
        (_SR_NN_, _L, _L),
        (_SR_NP_, _L, _H),
        (_SR_PN_, _H, _L),
        (_SR_PP_, _H, _H),
    ],
)
def test_yosys_sr_xx_(test_class, s_level, r_level):
    """Test _SR_XX_"""
    circuit = Circuit()
    _dut = test_class(circuit, "DUT")

    # Start with inactive
    _dut.S.value = inv(s_level)
    _dut.R.value = inv(r_level)
    # assert _dut.Q.value == "X"
    circuit.run(ms=1)
    # assert _dut.Q.value == "X"

    # SET
    _dut.S.value = s_level
    _dut.R.value = inv(r_level)
    circuit.run(ms=1)
    assert _dut.Q.value == 1

    # No action
    _dut.S.value = inv(s_level)
    _dut.R.value = inv(r_level)
    circuit.run(ms=1)
    assert _dut.Q.value == 1

    # RESET
    _dut.S.value = inv(s_level)
    _dut.R.value = r_level
    circuit.run(ms=1)
    assert _dut.Q.value == 0

    # No action
    _dut.S.value = inv(s_level)
    _dut.R.value = inv(r_level)
    circuit.run(ms=1)
    assert _dut.Q.value == 0


@pytest.mark.parametrize(
    "test_class, e_level, s_level, r_level",
    [
        (_DLATCHSR_NNN_, _L, _L, _L),
        (_DLATCHSR_NNP_, _L, _L, _H),
        (_DLATCHSR_NPN_, _L, _H, _L),
        (_DLATCHSR_NPP_, _L, _H, _H),
        (_DLATCHSR_PNN_, _H, _L, _L),
        (_DLATCHSR_PNP_, _H, _L, _H),
        (_DLATCHSR_PPN_, _H, _H, _L),
        (_DLATCHSR_PPP_, _H, _H, _H),
    ],
)
def test_yosys_dlatchsr_xxx_(test_class, e_level, s_level, r_level):
    """Test _DLATCHSR_XXX_"""
    circuit = Circuit()
    _dut = test_class(circuit, "DUT")

    # Enable Active

    _dut.E.value = e_level
    _dut.S.value = inv(s_level)
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

    # Set
    _dut.S.value = s_level
    circuit.run(ms=1)
    assert _dut.Q.value == 1

    _dut.S.value = inv(s_level)
    circuit.run(ms=1)
    assert _dut.Q.value == 1

    # Reset
    _dut.R.value = r_level
    circuit.run(ms=1)
    assert _dut.Q.value == 0

    _dut.R.value = inv(r_level)
    circuit.run(ms=1)
    assert _dut.Q.value == 0

    # Enable Active (with Set)
    _dut.E.value = e_level
    _dut.D.value = "X"
    _dut.S.value = s_level
    _dut.R.value = inv(r_level)
    circuit.run(ms=1)
    assert _dut.Q.value == 1

    # Enable Active (with Reset)
    _dut.E.value = e_level
    _dut.D.value = "X"
    _dut.S.value = inv(s_level)
    _dut.R.value = r_level
    circuit.run(ms=1)
    assert _dut.Q.value == 0


@pytest.mark.parametrize(
    "test_class, c_edge, s_level, r_level",
    [
        (_DFFSR_NNN_, _L, _L, _L),
        (_DFFSR_NNP_, _L, _L, _H),
        (_DFFSR_NPN_, _L, _H, _L),
        (_DFFSR_NPP_, _L, _H, _H),
        (_DFFSR_PNN_, _H, _L, _L),
        (_DFFSR_PNP_, _H, _L, _H),
        (_DFFSR_PPN_, _H, _H, _L),
        (_DFFSR_PPP_, _H, _H, _H),
    ],
)
def test_yosys_dffsr_xxx_(test_class, c_edge, s_level, r_level):
    """Test _DFFSR_XXX_"""
    circuit = Circuit()
    _dut = test_class(circuit, "DUT")

    _dut.C.value = inv(c_edge)
    _dut.S.value = inv(s_level)
    _dut.R.value = inv(r_level)
    _dut.D.value = 1
    # assert _dut.Q.value == "X"
    circuit.run(ms=1)
    # assert _dut.Q.value == "X"

    _dut.C.value = c_edge
    circuit.run(ms=1)
    assert _dut.Q.value == 1

    _dut.D.value = 0
    circuit.run(ms=1)
    assert _dut.Q.value == 1

    _dut.C.value = inv(c_edge)
    circuit.run(ms=1)
    assert _dut.Q.value == 1

    _dut.C.value = c_edge
    circuit.run(ms=1)
    assert _dut.Q.value == 0

    # Set
    _dut.S.value = s_level
    circuit.run(ms=1)
    assert _dut.Q.value == 1

    _dut.S.value = inv(s_level)
    circuit.run(ms=1)
    assert _dut.Q.value == 1

    # Reset
    _dut.R.value = r_level
    circuit.run(ms=1)
    assert _dut.Q.value == 0

    _dut.R.value = inv(r_level)
    circuit.run(ms=1)
    assert _dut.Q.value == 0


@pytest.mark.parametrize(
    "test_class, c_edge, s_level, r_level, e_level",
    [
        (_DFFSRE_NNNN_, _L, _L, _L, _L),
        (_DFFSRE_NNNP_, _L, _L, _L, _H),
        (_DFFSRE_NNPN_, _L, _L, _H, _L),
        (_DFFSRE_NNPP_, _L, _L, _H, _H),
        (_DFFSRE_NPNN_, _L, _H, _L, _L),
        (_DFFSRE_NPNP_, _L, _H, _L, _H),
        (_DFFSRE_NPPN_, _L, _H, _H, _L),
        (_DFFSRE_NPPP_, _L, _H, _H, _H),
        (_DFFSRE_PNNN_, _H, _L, _L, _L),
        (_DFFSRE_PNNP_, _H, _L, _L, _H),
        (_DFFSRE_PNPN_, _H, _L, _H, _L),
        (_DFFSRE_PNPP_, _H, _L, _H, _H),
        (_DFFSRE_PPNN_, _H, _H, _L, _L),
        (_DFFSRE_PPNP_, _H, _H, _L, _H),
        (_DFFSRE_PPPN_, _H, _H, _H, _L),
        (_DFFSRE_PPPP_, _H, _H, _H, _H),
    ],
)
def test_yosys_dffsre_xxxx_(test_class, c_edge, s_level, r_level, e_level):
    """Test _DLATCHSRE_XXXX_"""
    circuit = Circuit()
    _dut = test_class(circuit, "DUT")

    _dut.C.value = inv(c_edge)
    _dut.S.value = inv(s_level)
    _dut.R.value = inv(r_level)

    # Clock Enable = 0
    _dut.E.value = e_level

    _dut.D.value = 1
    # assert _dut.Q.value == "X"
    circuit.run(ms=1)
    # assert _dut.Q.value == "X"

    _dut.C.value = c_edge
    circuit.run(ms=1)
    assert _dut.Q.value == 1

    _dut.D.value = 0
    circuit.run(ms=1)
    assert _dut.Q.value == 1

    _dut.C.value = inv(c_edge)
    circuit.run(ms=1)
    assert _dut.Q.value == 1

    _dut.C.value = c_edge
    circuit.run(ms=1)
    assert _dut.Q.value == 0

    # Set
    _dut.S.value = s_level
    circuit.run(ms=1)
    assert _dut.Q.value == 1

    _dut.S.value = inv(s_level)
    circuit.run(ms=1)
    assert _dut.Q.value == 1

    # Reset
    _dut.R.value = r_level
    circuit.run(ms=1)
    assert _dut.Q.value == 0

    _dut.R.value = inv(r_level)
    circuit.run(ms=1)
    assert _dut.Q.value == 0

    # Clock Enable = 0
    _dut.E.value = inv(e_level)

    _dut.D.value = 1
    _dut.C.value = inv(c_edge)
    circuit.run(ms=1)
    assert _dut.Q.value == 0

    _dut.C.value = c_edge
    circuit.run(ms=1)
    assert _dut.Q.value == 0

    # Set (Clock Enable = 0)
    _dut.S.value = s_level
    circuit.run(ms=1)
    assert _dut.Q.value == 1

    _dut.S.value = inv(s_level)
    circuit.run(ms=1)
    assert _dut.Q.value == 1

    # Reset (Clock Enable = 0)
    _dut.R.value = r_level
    circuit.run(ms=1)
    assert _dut.Q.value == 0

    _dut.R.value = inv(r_level)
    circuit.run(ms=1)
    assert _dut.Q.value == 0
