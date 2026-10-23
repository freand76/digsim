# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""Test changing the settings of a Yosys component after it is made"""

import json
import tempfile
from pathlib import Path

import platformdirs
import pytest

from digsim.circuit import Circuit
from digsim.circuit.components import IntegratedCircuit, PushButton, YosysComponent
from digsim.circuit.components._yosys_component import YosysComponentException


ROOT = Path(__file__).parent.parent
TRAFFIC_LIGHT = ROOT / "examples" / "yosys_fsm" / "traffic_light.sv"
COUNTER = ROOT / "examples" / "yosys_counter" / "counter.v"


@pytest.fixture(name="work_dir")
def fixture_work_dir():
    """A folder Yosys can read: YoWASP has a private /tmp"""
    cache_dir = Path(platformdirs.user_cache_dir("digsim", appauthor=False))
    cache_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=cache_dir, ignore_cleanup_errors=True) as work_dir:
        yield Path(work_dir)


def _counter(path=COUNTER, **settings):
    """A counter with buttons on its inputs"""
    circuit = Circuit()
    counter = YosysComponent(circuit, path=path, **settings)
    buttons = {name: PushButton(circuit, name) for name in ("clk", "reset", "up")}
    for name, button in buttons.items():
        button.O.wire = counter.port(name)
    circuit.init()
    return circuit, counter, buttons


def _count(circuit, counter, buttons, clocks):
    """Reset the counter, and count some clock cycles"""
    buttons["reset"].push()
    circuit.run(ms=1)
    buttons["reset"].release()
    buttons["up"].push()
    for _ in range(clocks):
        buttons["clk"].push()
        circuit.run(ms=1)
        buttons["clk"].release()
        circuit.run(ms=1)
    return counter.cnt.value


def _cell_types(component):
    return sorted({type(cell).__name__ for cell in component._gates_comp._components})


def test_reconfigurable_parameters():
    _, counter, _ = _counter(functional=True)
    parameters = counter.get_reconfigurable_parameters()
    assert set(parameters) == {"functional", "signals"}
    assert parameters["functional"]["default"] is True
    assert parameters["signals"]["default"] is False


def test_ics_have_no_settings():
    ic = IntegratedCircuit(Circuit(), "74162")
    assert ic.get_reconfigurable_parameters() == {}


def test_functional_changes_the_cells():
    circuit, counter, buttons = _counter()
    gates = _cell_types(counter)
    assert _count(circuit, counter, buttons, 5) == 5
    counter.update_settings({"functional": True})
    assert counter.functional
    assert _cell_types(counter) != gates
    assert counter.settings_to_dict()["functional"] is True
    # The wires to the other components are kept, and it still counts
    circuit.init()
    assert _count(circuit, counter, buttons, 7) == 7
    counter.update_settings({"functional": False})
    assert _cell_types(counter) == gates
    assert "functional" not in counter.settings_to_dict()
    circuit.init()
    assert _count(circuit, counter, buttons, 3) == 3


def test_signals_and_states():
    circuit = Circuit()
    light = YosysComponent(circuit, path=TRAFFIC_LIGHT)
    with pytest.raises(YosysComponentException, match="signals=True"):
        light.signal("state")
    light.update_settings({"signals": True, "states": "timer"})
    circuit.init()
    assert light.state("state") == "X"
    assert light.state("timer") == "X"
    assert light.settings_to_dict()["states"] == "timer"
    light.update_settings({"signals": False})
    with pytest.raises(YosysComponentException, match="signals=True"):
        light.signal("state")


def test_same_settings_build_nothing():
    _, counter, _ = _counter()
    cells = list(counter._gates_comp._components)
    counter.update_settings({"functional": False, "signals": False, "states": ""})
    assert list(counter._gates_comp._components) == cells


def test_unknown_state_is_refused():
    circuit = Circuit()
    light = YosysComponent(circuit, path=TRAFFIC_LIGHT, signals=True)
    with pytest.raises(YosysComponentException, match="No signal 'missing'"):
        light.update_settings({"states": "missing", "functional": True})
    # The component and its settings are as before
    assert not light.functional
    assert light.parameter_get("states") == ""
    assert light.get_reconfigurable_parameters()["functional"]["default"] is False
    circuit.init()
    assert light.state("state") == "X"


def test_changed_ports_are_refused(work_dir):
    path = work_dir / "counter.v"
    path.write_text(COUNTER.read_text(encoding="utf-8"), encoding="utf-8")
    circuit, counter, buttons = _counter(path)
    path.write_text(
        "module counter(input clk, input reset, output [3:0] cnt);\n"
        "    assign cnt = 0;\n"
        "endmodule\n",
        encoding="utf-8",
    )
    with pytest.raises(YosysComponentException, match="reload the component first"):
        counter.update_settings({"functional": True})
    assert not counter.functional
    assert _count(circuit, counter, buttons, 2) == 2


def test_netlist_file_is_not_synthesized(work_dir, monkeypatch):
    path = work_dir / "counter.json"
    path.write_text(json.dumps(YosysComponent.synthesize_file(COUNTER)), encoding="utf-8")
    circuit, counter, buttons = _counter(path)
    monkeypatch.setattr(YosysComponent, "synthesize_file", None)
    counter.update_settings({"functional": True})
    assert counter.functional
    circuit.init()
    assert _count(circuit, counter, buttons, 4) == 4


def test_netlist_has_no_synthesis_setting(work_dir):
    """A netlist is not synthesized: Settings has only the internal signals"""
    path = work_dir / "counter.json"
    path.write_text(json.dumps(YosysComponent.synthesize_file(COUNTER)), encoding="utf-8")
    _, counter, _ = _counter(path)
    assert set(counter.get_reconfigurable_parameters()) == {"signals"}
    _, verilog_counter, _ = _counter()
    assert set(verilog_counter.get_reconfigurable_parameters()) == {"functional", "signals"}
