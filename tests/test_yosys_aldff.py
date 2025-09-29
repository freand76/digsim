# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Pystest module to test functionality of yosys asynchronous load dff"""

import pytest
from utilities import _H, _L, inv

from digsim.circuit import Circuit
from digsim.circuit.components._yosys_atoms import (
    _ALDFF_NN_,
    _ALDFF_NP_,
    _ALDFF_PN_,
    _ALDFF_PP_,
    _ALDFFE_NNN_,
    _ALDFFE_NNP_,
    _ALDFFE_NPN_,
    _ALDFFE_NPP_,
    _ALDFFE_PNN_,
    _ALDFFE_PNP_,
    _ALDFFE_PPN_,
    _ALDFFE_PPP_,
)


@pytest.mark.parametrize(
    "test_class, c_edge, l_level",
    [
        (_ALDFF_NN_, _L, _L),
        (_ALDFF_NP_, _L, _H),
        (_ALDFF_PN_, _H, _L),
        (_ALDFF_PP_, _H, _H),
    ],
)
def test_yosys_aldff_Xx_(test_class, c_edge, l_level):
    """Test _ALDFF_XX_"""
    circuit = Circuit()
    _dut = test_class(circuit, "DUT")

    # Start before clock edge
    _dut.C.value = inv(c_edge)
    _dut.L.value = inv(l_level)
    _dut.D.value = 0
    _dut.AD.value = 0
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

    # Asynchronous load
    _dut.AD.value = 0
    _dut.L.value = l_level
    circuit.run(ms=1)
    assert _dut.Q.value == 0

    _dut.AD.value = 1
    _dut.L.value = inv(l_level)
    circuit.run(ms=1)
    assert _dut.Q.value == 0

    _dut.L.value = l_level
    circuit.run(ms=1)
    assert _dut.Q.value == 1


@pytest.mark.parametrize(
    "test_class, c_edge, l_level, e_level",
    [
        (_ALDFFE_NNN_, _L, _L, _L),
        (_ALDFFE_NNP_, _L, _L, _H),
        (_ALDFFE_NPN_, _L, _H, _L),
        (_ALDFFE_NPP_, _L, _H, _H),
        (_ALDFFE_PNN_, _H, _L, _L),
        (_ALDFFE_PNP_, _H, _L, _H),
        (_ALDFFE_PPN_, _H, _H, _L),
        (_ALDFFE_PPP_, _H, _H, _H),
    ],
)
def test_yosys_aldffe_xxx_(test_class, c_edge, l_level, e_level):
    """Test _ALDFFE_XXX_"""
    circuit = Circuit()
    _dut = test_class(circuit, "DUT")

    # Clock Enable = 1
    _dut.E.value = e_level

    # Start before clock edge
    _dut.C.value = inv(c_edge)
    _dut.L.value = inv(l_level)
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

    # Asynchronous load
    _dut.AD.value = 0
    _dut.L.value = l_level
    circuit.run(ms=1)
    assert _dut.Q.value == 0

    _dut.AD.value = 1
    _dut.L.value = inv(l_level)
    circuit.run(ms=1)
    assert _dut.Q.value == 0

    _dut.L.value = l_level
    circuit.run(ms=1)
    assert _dut.Q.value == 1

    # Clock Enable = 0
    _dut.AD.value = 0
    _dut.L.value = inv(l_level)
    _dut.E.value = inv(e_level)

    _dut.D.value = 0
    _dut.C.value = inv(c_edge)
    circuit.run(ms=1)
    assert _dut.Q.value == 1

    _dut.C.value = c_edge
    circuit.run(ms=1)
    assert _dut.Q.value == 1

    # Asynchronous load (While clock enable = 0)
    _dut.AD.value = 0
    _dut.L.value = l_level
    circuit.run(ms=1)
    assert _dut.Q.value == 0

    _dut.AD.value = 1
    _dut.L.value = inv(l_level)
    circuit.run(ms=1)
    assert _dut.Q.value == 0

    _dut.L.value = l_level
    circuit.run(ms=1)
    assert _dut.Q.value == 1
