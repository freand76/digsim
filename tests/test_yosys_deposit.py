# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""
Pytest module to test deposits on the signals inside a Yosys component, with the Python
engine and the native engine (with its blocks and with its cells)
"""

from pathlib import Path

import pytest

from digsim.circuit import Circuit, _native
from digsim.circuit.components import YosysComponent, YosysComponentException
from digsim.synth import Synthesis
from digsim.utils import YosysNetlist


DEPOSIT = Path(__file__).parent / "verilog" / "synth_deposit.sv"
NATIVE = _native.digsim_native is not None
DEPOSITS = NATIVE and _native.digsim_native.INTERFACE >= 6

ENGINES = [
    pytest.param({"DIGSIM_ENGINE": "python"}, id="python"),
    pytest.param(
        {}, id="native-blocks", marks=pytest.mark.skipif(not DEPOSITS, reason="digsim-native")
    ),
    pytest.param(
        {"DIGSIM_BLOCKS": "0"},
        id="native-cells",
        marks=pytest.mark.skipif(not DEPOSITS, reason="digsim-native"),
    ),
]


def _deposit(monkeypatch, environment, functional, vcd=None):
    """The design, its signals kept, set up with the counter at 0"""
    monkeypatch.delenv("DIGSIM_ENGINE", raising=False)
    monkeypatch.delenv("DIGSIM_BLOCKS", raising=False)
    for name, value in environment.items():
        monkeypatch.setenv(name, value)
    netlist = Synthesis(
        str(DEPOSIT), "deposit", functional=functional, keep_signals=True
    ).synth_to_dict(silent=True)
    circuit = Circuit(vcd=vcd)
    top = YosysComponent(circuit, signals=True)
    top.create_from_netlist(YosysNetlist(**netlist))
    circuit.init()
    top.clk.value = 0
    top.ena.value = 0
    top.a.value = 0
    circuit.run(us=1)
    top.deposit("count", 0)
    circuit.run(us=1)
    return circuit, top


def _clock(circuit, top):
    top.clk.value = 1
    circuit.run(us=1)
    top.clk.value = 0
    circuit.run(us=1)


@pytest.mark.parametrize("functional", [False, True])
@pytest.mark.parametrize("environment", ENGINES)
def test_deposit_register(monkeypatch, environment, functional):
    """A register keeps a deposit until its next active edge, the logic after it sees it"""
    circuit, top = _deposit(monkeypatch, environment, functional)
    assert top.signal("count") == 0
    top.deposit("count", 5)
    assert top.signal("count") == 5
    circuit.run(us=1)
    assert top.signal("count_plus_one") == 6
    assert top.y.value == 0xF ^ 6
    # Not enabled: no active edge, the register keeps the deposit
    _clock(circuit, top)
    assert top.signal("count") == 5
    top.ena.value = 1
    _clock(circuit, top)
    assert top.signal("count") == 6
    # One bit, and an undefined bit
    top.deposit("count", 1, bit=3)
    assert top.signal("count") == 0b1110
    top.deposit("count", "X", bit=0)
    assert top.signal("count") == "X"
    top.deposit("count", 2)
    circuit.run(us=1)
    assert top.signal("count_plus_one") == 3


@pytest.mark.parametrize("functional", [False, True])
@pytest.mark.parametrize("environment", ENGINES)
def test_deposit_logic(monkeypatch, environment, functional):
    """
    Logic keeps a deposit until one of its inputs changes: in a netlist of gates each bit
    of a_inv has a gate of its own, a functional netlist has one cell for all
    """
    circuit, top = _deposit(monkeypatch, environment, functional)
    assert top.signal("a_inv") == 0xF
    top.deposit("a_inv", 0b1010)
    assert top.signal("a_inv") == 0b1010
    circuit.run(us=1)
    assert top.y.value == 0b1010 ^ 1
    # The other bits of a don't change
    top.a.value = 0b0011
    circuit.run(us=1)
    assert top.signal("a_inv") == (0b1000 if not functional else 0b1100)
    assert top.y.value == top.signal("a_inv") ^ 1
    top.a.value = 0b1111
    circuit.run(us=1)
    assert top.signal("a_inv") == 0


@pytest.mark.parametrize("environment", ENGINES)
def test_deposit_input_and_constant(monkeypatch, environment):
    """
    A signal that is an input (mixed[0] is a[0]) has a buffer of its own, it keeps a
    deposit until the input changes. A constant bit, or no signal, can't be deposited.
    """
    circuit, top = _deposit(monkeypatch, environment, False)
    assert top.signal("mixed") == 0b10
    top.deposit("mixed", 1, bit=0)
    assert top.signal("mixed") == 0b11
    assert top.a.value == 0
    top.a.value = 0b0001
    circuit.run(us=1)
    top.a.value = 0
    circuit.run(us=1)
    assert top.signal("mixed") == 0b10
    with pytest.raises(YosysComponentException, match="constant"):
        top.deposit("mixed", 0, bit=1)
    with pytest.raises(YosysComponentException, match="No signal"):
        top.deposit("missing", 0)


@pytest.mark.parametrize("environment", ENGINES)
def test_deposit_in_vcd(monkeypatch, tmp_path, environment):
    """The VCD file has the deposit, at its time"""
    vcd = tmp_path / "deposit.vcd"
    circuit, top = _deposit(monkeypatch, environment, False, vcd=str(vcd))
    time = circuit.time_ns
    top.deposit("count", 5)
    circuit.run(us=1)
    circuit.vcd_close()
    text = vcd.read_text(encoding="utf-8")
    variable = next(
        line.split()[3]
        for line in text.splitlines()
        if line.startswith("$var") and line.split()[4] == "count"
    )
    changes = text.split(f"#{time}\n", 1)[1].split("#", 1)[0]
    assert f"b101 {variable}" in changes.splitlines()


@pytest.mark.skipif(not NATIVE or DEPOSITS, reason="an older digsim-native")
def test_deposit_older_native(monkeypatch):
    """An older digsim-native can't deposit with its engine"""
    _circuit, top = _deposit(monkeypatch, {"DIGSIM_ENGINE": "python"}, False)
    monkeypatch.delenv("DIGSIM_ENGINE")
    circuit = Circuit()
    netlist = Synthesis(str(DEPOSIT), "deposit", keep_signals=True).synth_to_dict(silent=True)
    top = YosysComponent(circuit, signals=True)
    top.create_from_netlist(YosysNetlist(**netlist))
    circuit.init()
    circuit.run(us=1)
    with pytest.raises(YosysComponentException, match="digsim-native 0.6.0"):
        top.deposit("count", 5)
