# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""
The flip-flops and latches of a Yosys component start undefined ("X"), or at the initial
value of the Verilog (the init attribute of the net, like "reg ready = 0")
"""

from pathlib import Path

import pytest

from digsim.circuit import Circuit
from digsim.circuit.components import YosysComponent
from digsim.circuit.components._yosys_atoms import _DFF_P_, _DLATCH_P_, _SR_PP_
from digsim.utils import YosysModule


# Also on the other platforms: Yosys and the native engine (see .github/workflows)
pytestmark = pytest.mark.sanity


INITIAL_VALUES = Path(__file__).parent / "verilog" / "initial_values.v"


@pytest.mark.parametrize("cls", [_DFF_P_, _DLATCH_P_, _SR_PP_])
def test_gate_register_starts_undefined(cls):
    """A gate flip-flop or latch is "X" after init, or its initial value"""
    circuit = Circuit()
    register = cls(circuit, "DUT")
    circuit.init()
    circuit.run(ms=1)
    assert register.Q.value == "X"

    register.initial_value = 1
    circuit.init()
    circuit.run(ms=1)
    assert register.Q.value == 1


def test_initial_values_of_nets():
    """The init attributes of the signals, as values of their nets ("x" bits have none)"""
    module = YosysModule(
        netnames={
            "a": {"bits": [2, 3, 4, 5], "attributes": {"init": "10x1"}},
            "b": {"bits": [6, 7], "attributes": {"init": 2}},
            "c": {"bits": [8], "attributes": {}},
        }
    )
    assert module.initial_values() == {2: 1, 4: 0, 5: 1, 6: 0, 7: 1}


def _component(functional):
    circuit = Circuit()
    component = YosysComponent(circuit, path=INITIAL_VALUES, functional=functional)
    circuit.init()
    _inputs(component, clk=0, we=0, addr=2, din=0x77)
    circuit.run(ms=1)
    return circuit, component


def _inputs(component, **values):
    for name, value in values.items():
        component.port(name).value = value


def _clock(circuit, component):
    _inputs(component, clk=1)
    circuit.run(ms=1)
    _inputs(component, clk=0)
    circuit.run(ms=1)


@pytest.mark.parametrize("functional", [False, True])
def test_registers_start_at_initial_values(functional):
    """A register with an initial value starts at it, the others are "X" until written"""
    _circuit, component = _component(functional)
    assert component.inited.value == 0xA5
    assert component.plain.value == "X"
    assert component.ram_out.value == "X"
    # 4'b10xx: the bits without an initial value are "X"
    partial = [component.partial.get_bit(bit).value for bit in range(4)]
    assert partial == ["X", "X", 0, 1]


@pytest.mark.parametrize("functional", [False, True])
def test_memory_initial_contents(functional):
    """The initial contents of a memory (mapped to registers) can be read"""
    circuit, component = _component(functional)
    for addr, value in enumerate((0x11, 0x22, 0x33, 0x44)):
        _inputs(component, addr=addr)
        circuit.run(ms=1)
        _clock(circuit, component)
        assert component.ram_out.value == value


@pytest.mark.parametrize("functional", [False, True])
def test_init_restores_initial_values(functional):
    """A new init sets the registers back to their initial values, after writes"""
    circuit, component = _component(functional)
    _inputs(component, we=1)
    circuit.run(ms=1)
    _clock(circuit, component)
    assert component.inited.value == 0x77
    assert component.plain.value == 0x77
    assert component.partial.value == 0x7

    circuit.init()
    _inputs(component, clk=0, we=0, addr=2, din=0x77)
    circuit.run(ms=1)
    assert component.inited.value == 0xA5
    assert component.plain.value == "X"
    # The memory is registers: its contents are the initial ones again
    _clock(circuit, component)
    assert component.ram_out.value == 0x33
