# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Pytest module to test the named signals and states of Yosys components"""

from pathlib import Path

import pytest

from digsim.circuit import Circuit
from digsim.circuit.components import YosysComponent
from digsim.circuit.components._yosys_component import YosysComponentException
from digsim.utils import YosysModule, YosysNetname


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
