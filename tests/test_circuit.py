# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Pytest module to test the Circuit class"""

from pathlib import Path

import pytest

from digsim.circuit import Circuit
from digsim.circuit.components import AND, SR, Led, PushButton, YosysComponent
from digsim.storage_model import CircuitDataClass, ComponentDataClass


def test_delete_component():
    """A deleted component is removed from the circuit and disconnected"""
    circuit = Circuit()
    button = PushButton(circuit, "button")
    gate = AND(circuit, "gate")
    button.O.wire = gate.A
    circuit.delete_component(gate)
    assert [component.name() for component in circuit.components] == ["button"]
    assert button.O.wired_ports == []


def test_deleted_component_events_dont_drive():
    """An event that a deleted component had in the queue doesn't set its old wires"""
    circuit = Circuit()
    button = PushButton(circuit, "button")
    gate = AND(circuit, "gate")
    led = Led(circuit, "led")
    button.O.wire = gate.A
    button.O.wire = gate.B
    gate.Y.wire = led.I
    circuit.init()
    button.push()
    circuit.run(ns=0)  # The gate's output event is in the queue
    circuit.delete_component(gate)
    circuit.run(ms=1)
    assert led.I.value == "X"


def test_delete_multi_component():
    """Deleting a component built from other components removes them too"""
    circuit = Circuit()
    latch = SR(circuit, "latch")
    led = Led(circuit, "led")
    latch.Q.wire = led.I
    assert len(circuit.components) == 4  # the latch, its two NOR gates and the LED
    circuit.delete_component(latch)
    assert [component.name() for component in circuit.components] == ["led"]


def test_delete_yosys_component():
    """Deleting a Yosys component removes all its gates"""
    circuit = Circuit()
    counter = YosysComponent(circuit, path="examples/yosys_counter/counter.json")
    Led(circuit, "led")
    assert len(circuit.components) > 2
    circuit.delete_component(counter)
    assert [component.name() for component in circuit.components] == ["led"]


def test_context_manager_closes_vcd(tmp_path):
    """A circuit used in a with statement closes its VCD file at the end"""
    vcd_path = tmp_path / "with.vcd"
    with Circuit(vcd=str(vcd_path)) as circuit:
        button = PushButton(circuit, "button")
        circuit.init()
        button.push()
        circuit.run(ms=1)
    # Without closing, the VCD writer would still hold the values in its buffer
    assert "$dumpvars" in vcd_path.read_text()


def test_reload_yosys_component():
    """Reloading a Yosys component replaces its gates, and the counter still counts"""
    circuit = Circuit()
    counter = YosysComponent(circuit, path="examples/yosys_counter/counter.json")
    clock = PushButton(circuit, "clock")
    clock.O.wire = counter.clk
    component_count = len(circuit.components)
    counter.reload_file()
    assert len(circuit.components) == component_count

    circuit.init()
    counter.up.value = 1
    counter.reset.value = 1
    circuit.run(ms=1)
    counter.reset.value = 0
    circuit.run(ms=1)
    for expected in range(1, 4):
        clock.push()
        circuit.run(ms=1)
        clock.release()
        circuit.run(ms=1)
        assert counter.cnt.value == expected


def test_failed_component_not_left_in_circuit(tmp_path):
    """A component that fails to load is not left in the circuit, nor are its parts"""
    circuit_dc = CircuitDataClass(
        components=[
            ComponentDataClass(
                name="counter",
                type="digsim.circuit.components.YosysComponent",
                settings={"path": str(tmp_path / "missing.json")},
            ),
            ComponentDataClass(name="led", type="digsim.circuit.components.Led"),
        ]
    )
    circuit = Circuit()
    exceptions = circuit.from_dataclass(circuit_dc, component_exceptions=False)
    assert len(exceptions) == 1
    assert [component.name() for component in circuit.components] == ["led"]


def test_load_same_dataclass_twice():
    """Loading a component keeps its stored relative path unchanged"""
    component_dc = ComponentDataClass(
        name="counter",
        type="digsim.circuit.components.YosysComponent",
        settings={"path": "counter.json"},
    )
    circuit_dc = CircuitDataClass(components=[component_dc])
    for _ in range(2):
        Circuit().from_dataclass(circuit_dc, folder="examples/yosys_counter")
    assert component_dc.settings == {"path": "counter.json"}


def test_adding_components_removes_on_error():
    """Components added in a failing adding_components block are removed again"""
    circuit = Circuit()
    PushButton(circuit, "button")
    with pytest.raises(ValueError), circuit.adding_components():
        SR(circuit, "latch")
        raise ValueError
    assert [component.name() for component in circuit.components] == ["button"]
    with circuit.adding_components():
        Led(circuit, "led")
    assert [component.name() for component in circuit.components] == ["button", "led"]


def test_vcd_that_cannot_be_opened(tmp_path):
    """A VCD file that can't be opened is not left half started"""
    circuit = Circuit()
    button = PushButton(circuit, "button")
    circuit.init()
    with pytest.raises(OSError):
        circuit.vcd(str(tmp_path / "missing" / "waves.vcd"))
    button.push()
    circuit.run(ms=1)
    circuit.vcd(str(tmp_path / "waves.vcd"))
    circuit.vcd_close()
    assert (tmp_path / "waves.vcd").exists()


def test_sub_components_initialized_once():
    """The circuit initializes each component once, also the parts of a component"""
    calls = []

    class CountingAND(AND):
        def init(self):
            calls.append("init")
            super().init()

        def default_state(self):
            calls.append("default_state")
            super().default_state()

    circuit = Circuit()
    latch = SR(circuit, "latch")
    latch.add(CountingAND(circuit, "part"))
    circuit.init()
    assert calls == ["init", "default_state"]


def _yosys_circuit_dc(netlist_path):
    return CircuitDataClass(
        name="circuit",
        components=[
            ComponentDataClass(
                name="counter",
                type="digsim.circuit.components.YosysComponent",
                settings={"path": netlist_path},
            )
        ],
    )


def test_stored_paths_use_forward_slashes(tmp_path):
    """Paths are stored relative to the circuit folder with '/', which Linux and Windows read"""
    netlist = Path(__file__).parent.parent / "examples" / "yosys_counter" / "counter.json"
    (tmp_path / "designs" / "counter").mkdir(parents=True)
    (tmp_path / "circuits").mkdir()
    netlist_copy = tmp_path / "designs" / "counter" / "counter.json"
    netlist_copy.write_text(netlist.read_text())
    circuit = Circuit(name="circuit")
    YosysComponent(circuit, path=netlist_copy)
    stored = circuit.to_dataclass(str(tmp_path / "circuits")).components[0].settings["path"]
    assert stored == "../designs/counter/counter.json"
    loaded = Circuit()
    loaded.from_dataclass(_yosys_circuit_dc(stored), str(tmp_path / "circuits"))
    assert len(loaded.components) > 1


def test_load_path_stored_on_windows(tmp_path):
    """A path stored with '\\' (on Windows, by older versions) is loaded on all systems"""
    netlist = Path(__file__).parent.parent / "examples" / "yosys_counter" / "counter.json"
    (tmp_path / "designs").mkdir()
    (tmp_path / "circuits").mkdir()
    (tmp_path / "designs" / "counter.json").write_text(netlist.read_text())
    loaded = Circuit()
    loaded.from_dataclass(
        _yosys_circuit_dc("..\\designs\\counter.json"), str(tmp_path / "circuits")
    )
    assert len(loaded.components) > 1


def _counter_project(tmp_path):
    """A project folder with a netlist in 'designs' and a circuit saved in 'circuits'"""
    netlist = Path(__file__).parent.parent / "examples" / "yosys_counter" / "counter.json"
    (tmp_path / "designs").mkdir()
    (tmp_path / "circuits").mkdir()
    (tmp_path / "designs" / "counter.json").write_text(netlist.read_text())


def test_json_file_paths_relative_to_file(tmp_path, monkeypatch):
    """A saved circuit file loads from any working directory"""
    _counter_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    circuit = Circuit(name="circuit")
    YosysComponent(circuit, path="designs/counter.json")
    circuit.to_json_file("circuits/counter_circuit.json")
    stored = (tmp_path / "circuits" / "counter_circuit.json").read_text()
    assert '"path": "../designs/counter.json"' in stored
    for working_dir, filename in [
        (tmp_path, "circuits/counter_circuit.json"),
        (tmp_path / "circuits", "counter_circuit.json"),
        (tmp_path / "designs", "../circuits/counter_circuit.json"),
    ]:
        monkeypatch.chdir(working_dir)
        loaded = Circuit()
        loaded.from_json_file(filename)
        assert len(loaded.components) > 1


def test_json_file_explicit_folder(tmp_path, monkeypatch):
    """A file with paths relative to another folder loads with that folder"""
    _counter_project(tmp_path)
    (tmp_path / "circuits" / "old.json").write_text(
        '{"circuit": {"name": "c", "components": [{"name": "counter", '
        '"type": "digsim.circuit.components.YosysComponent", '
        '"settings": {"path": "designs/counter.json"}}], "wires": []}}'
    )
    monkeypatch.chdir(tmp_path)
    loaded = Circuit()
    loaded.from_json_file("circuits/old.json", folder=".")
    assert len(loaded.components) > 1


def test_process_single_event():
    """Events can be processed one at a time, the public way to step through a simulation"""
    circuit = Circuit()
    button = PushButton(circuit, "button")
    led = Led(circuit, "led")
    button.O.wire = led.I
    circuit.init()
    button.push()
    assert circuit.process_single_event() == (True, True)
    assert led.I.value == 1
    assert circuit.process_single_event() == (False, False)
    # Events after the stop time are kept for later
    button.release()
    gate = AND(circuit, "gate")
    gate.A.value = 1
    gate.B.value = 1
    assert circuit.process_single_event(stop_time_ns=circuit.time_ns) == (True, True)
    assert circuit.process_single_event(stop_time_ns=circuit.time_ns) == (False, False)
    assert circuit.process_single_event() == (True, True)
    assert gate.Y.value == 1


def test_clear_removes_pending_events():
    """Clearing a circuit also drops the events of the removed components"""
    circuit = Circuit()
    button = PushButton(circuit, "button")
    circuit.init()
    button.push()
    circuit.clear()
    assert circuit.process_single_event() == (False, False)
