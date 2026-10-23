# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""Pytest module to test the named signals and states of Yosys components"""

import json
from pathlib import Path

import pytest

from digsim.circuit import Circuit
from digsim.circuit.components import YosysComponent
from digsim.circuit.components._yosys_component import YosysComponentException
from digsim.synth import Synthesis
from digsim.utils import YosysModule, YosysNetlist, YosysNetname


TRAFFIC_LIGHT = Path(__file__).parent.parent / "examples" / "yosys_fsm" / "traffic_light.sv"


def test_enum_names():
    """The names of the values of a SystemVerilog enum, from the attributes of the signal"""
    netname = YosysNetname(
        bits=[2, 3],
        attributes={
            "enum_type": "$enum0",
            "enum_value_00": "\\IDLE",
            "enum_value_10": "\\DONE",
            "src": "fsm.sv:3.11-3.16",
        },
    )
    assert netname.enum_names() == {0: "IDLE", 2: "DONE"}


def test_state_names_from_parameters():
    """Without an enum, the parameters with the width of the signal name the values"""
    module = YosysModule(
        netnames={
            "state": YosysNetname(bits=[2, 3]),
            "$auto$made_up": YosysNetname(bits=[4]),
            "hidden": YosysNetname(bits=[5], hide_name=1),
            "constant": YosysNetname(bits=["0"]),
        },
        parameter_default_values={"IDLE": "00", "RUN": "01", "GO": "01", "WIDE": "0001"},
    )
    assert module.signal_names() == ["state"]
    assert module.state_names("state") == {0: "IDLE", 1: "RUN/GO"}


def _traffic_light(functional, vcd=None):
    circuit = Circuit(vcd=vcd)
    light = YosysComponent(circuit, path=TRAFFIC_LIGHT, functional=functional, signals=True)
    circuit.init()
    light.clk.value = 0
    light.request.value = 0
    light.reset.value = 1
    return circuit, light


def _clock(circuit, light):
    light.clk.value = 1
    circuit.run(us=1)
    light.clk.value = 0
    circuit.run(us=1)


@pytest.mark.parametrize("functional", [False, True])
def test_traffic_light_states(functional):
    """The state and the timer of the traffic light, with the names of the states"""
    circuit, light = _traffic_light(functional)
    assert light.signal_names() == ["state", "timer"]
    _clock(circuit, light)
    light.reset.value = 0
    light.request.value = 1
    states = []
    for _ in range(11):
        _clock(circuit, light)
        states.append(light.state("state"))
    assert states == [
        "RED",
        "RED_YELLOW",
        "RED_YELLOW",
        "GREEN",
        "GREEN",
        "GREEN",
        "GREEN",
        "GREEN",
        "YELLOW",
        "YELLOW",
        "RED",
    ]
    # The timer counts down in each state, from 2 after yellow
    assert light.signal("timer") == 2
    assert light.signal("state") == 0


def test_states_in_vcd(tmp_path):
    """The state is written to the VCD file as text, the other signals as wires"""
    vcd = tmp_path / "light.vcd"
    circuit, light = _traffic_light(True, vcd=str(vcd))
    _clock(circuit, light)
    light.reset.value = 0
    light.request.value = 1
    for _ in range(5):
        _clock(circuit, light)
    circuit.vcd_close()
    text = vcd.read_text()
    assert "$var string 1" in text
    assert "$var wire 3" in text
    assert "sRED_YELLOW" in text
    assert "sGREEN" in text


def test_signal_errors():
    """Without signals=True, or for a signal without names, a clear error"""
    circuit = Circuit()
    plain = YosysComponent(circuit, path=TRAFFIC_LIGHT)
    assert plain.signal_names() == ["state", "timer"]
    with pytest.raises(YosysComponentException, match="signals=True"):
        plain.signal("state")
    _, light = _traffic_light(True)
    with pytest.raises(YosysComponentException, match="No signal"):
        light.signal("missing")
    with pytest.raises(YosysComponentException, match="no names"):
        light.state("timer")
    with pytest.raises(YosysComponentException, match="state names"):
        YosysComponent(Circuit(), path=TRAFFIC_LIGHT, signals=True, states="missing")


def test_signal_settings():
    """The settings are only stored when used, and the states as a text"""
    circuit = Circuit()
    plain = YosysComponent(circuit, path=TRAFFIC_LIGHT)
    assert set(plain.settings_to_dict()) == {"path"}
    named = YosysComponent(circuit, path=TRAFFIC_LIGHT, signals=True, states=["timer"])
    settings = named.settings_to_dict()
    assert settings["signals"] is True
    assert settings["states"] == "timer"
    again = YosysComponent(Circuit(), **settings)
    assert again.state("timer") == "X"


def test_signals_after_reload():
    """Reloading the file makes the signals again"""
    circuit, light = _traffic_light(True)
    light.reload_file()
    circuit.init()
    assert light.state("state") == "X"
    assert light.signal_names() == ["state", "timer"]


# The named signals that DigSim reads from Yosys netlists. These tests synthesize with the
# bundled Yosys, so that an upgrade of Yosys that renames or drops them is noticed.

REPO = Path(__file__).parent.parent
CPU_FILES = [str(REPO / "verilog" / "6502" / "ALU.v"), str(REPO / "verilog" / "6502" / "cpu.v")]
# Signal name: width, of the 6502 (registers, the state, and a signal of the submodule)
CPU_SIGNALS = {
    "PC": 16,
    "PCH": 8,
    "PCL": 8,
    "IR": 8,
    "P": 8,
    "AXYS[0]": 8,
    "AXYS[1]": 8,
    "AXYS[2]": 8,
    "AXYS[3]": 8,
    "state": 6,
    "ALU.OUT": 8,
}
# Some of the states of the 6502, from the parameters in cpu.v
CPU_STATES = {8: "BRK0", 12: "DECODE", 13: "FETCH", 36: "REG"}


def _check_cpu_module(module):
    names = module.signal_names()
    for name, width in CPU_SIGNALS.items():
        assert name in names, name
        assert len(module.netnames[name].bits) == width, name
    states = module.state_names("state")
    assert len(states) == 50
    assert all(states[value] == name for value, name in CPU_STATES.items())


@pytest.mark.parametrize("functional", [False, True])
def test_cpu_signals_from_yosys(functional):
    """The 6502 synthesized now has its registers, its state and the names of its states"""
    netlist = YosysNetlist(
        **Synthesis(CPU_FILES, "cpu", functional=functional).synth_to_dict(silent=True)
    )
    _check_cpu_module(netlist.modules["cpu"])


@pytest.mark.parametrize("netlist_file", ["6502_primitives.json", "6502_functional.json"])
def test_cpu_signals_in_example_netlists(netlist_file):
    """The netlists of the 6502 example have the same signals and states"""
    path = REPO / "examples" / "yosys_6502" / netlist_file
    netlist = YosysNetlist(**json.loads(path.read_text()))
    _check_cpu_module(netlist.modules["cpu"])


@pytest.mark.parametrize("functional", [False, True])
def test_enum_states_from_yosys(functional):
    """
    The states of a SystemVerilog enum keep their names and encoding: the functional
    synthesis doesn't make the state register one-hot
    """
    synthesis = Synthesis([str(TRAFFIC_LIGHT)], "traffic_light", functional=functional)
    module = YosysNetlist(**synthesis.synth_to_dict(silent=True)).modules["traffic_light"]
    assert module.signal_names() == ["state", "timer"]
    assert len(module.netnames["state"].bits) == 2
    assert module.netnames["state"].enum_names() == {
        0: "RED",
        1: "RED_YELLOW",
        2: "GREEN",
        3: "YELLOW",
    }
    assert len(module.netnames["timer"].bits) == 3


FSM_PARAMETERS = Path(__file__).parent / "verilog" / "fsm_parameters.v"


def test_named_automatically():
    """
    With signals, every signal with names for its values has them: an enum, or a signal
    with the width of at least two parameters. Not one bit wide, like flag.
    """
    circuit = Circuit()
    fsm = YosysComponent(circuit, path=FSM_PARAMETERS, signals=True)
    circuit.init()
    assert fsm.state("state") == "X"
    assert fsm.state("other") == "X"
    with pytest.raises(YosysComponentException, match="no names"):
        fsm.state("flag")
    # 'states' names more signals, also of one bit
    fsm = YosysComponent(Circuit(), path=FSM_PARAMETERS, signals=True, states="flag")
    assert fsm.state("flag") == "X"


def _fsm(vcd=None):
    circuit = Circuit(vcd=vcd)
    fsm = YosysComponent(circuit, path=FSM_PARAMETERS, signals=True)
    circuit.init()
    fsm.reset.value = 1
    fsm.clk.value = 0
    return circuit, fsm


def test_value_and_names():
    """A named signal has its value and its names, the names in a port of its own"""
    circuit, fsm = _fsm()
    fsm.clk.value = 1
    circuit.run(us=1)
    fsm.clk.value = 0
    fsm.reset.value = 0
    circuit.run(us=1)
    fsm.clk.value = 1
    circuit.run(us=1)
    assert fsm.signal("state") == 1
    assert fsm.state("state") == "RUN"
    # The design's own state_name signal keeps its name
    assert fsm.signal("state_name") == 1
    assert fsm.state("other") == "RUN"


def test_value_and_names_in_vcd(tmp_path):
    vcd = tmp_path / "fsm.vcd"
    circuit, fsm = _fsm(vcd=str(vcd))
    for reset in (1, 0, 0):
        fsm.reset.value = reset
        fsm.clk.value = 1
        circuit.run(us=1)
        fsm.clk.value = 0
        circuit.run(us=1)
    circuit.vcd_close()
    variables = {
        fields[4]: (fields[1], fields[2])
        for fields in (line.split() for line in vcd.read_text().splitlines())
        if fields and fields[0] == "$var"
    }
    # The value as a number, the names as text, and the design's own state_name
    assert variables["state"] == ("wire", "2")
    assert variables["state_name_"] == ("string", "1")
    assert variables["state_name"] == ("wire", "4")
    assert variables["other_name"] == ("string", "1")
    assert "flag_name" not in variables
    text = vcd.read_text()
    assert "sRUN" in text and "sDONE" in text
