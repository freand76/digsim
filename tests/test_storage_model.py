# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Pytest module to test the storage model data classes"""

import pytest

from digsim.circuit import Circuit
from digsim.circuit.components import Led, PushButton
from digsim.circuit.components.atoms import DigsimException
from digsim.storage_model import (
    AppFileDataClass,
    CircuitDataClass,
    CircuitFileDataClass,
    ComponentDataClass,
    GuiWireDataClass,
    ModelDataClass,
)


def test_model_dataclass_keeps_shortcuts():
    """The model state (also used for undo) holds the shortcuts of a loaded file"""
    app_file_dc = AppFileDataClass(circuit=CircuitDataClass(), shortcuts={"1": "button"})
    assert ModelDataClass.from_app_file_dc(app_file_dc).shortcuts == {"1": "button"}


@pytest.mark.parametrize("content", ["[]", "3", '"text"', "{"])
@pytest.mark.parametrize("file_class", [AppFileDataClass, CircuitFileDataClass])
def test_malformed_circuit_file(tmp_path, content, file_class):
    """A file that is not a JSON object is reported as malformed (ValueError)"""
    filename = tmp_path / "bad.circuit"
    filename.write_text(content)
    with pytest.raises(ValueError, match="Malformed"):
        file_class.load(filename)


def test_circuit_file_round_trip(tmp_path):
    """A saved circuit file loads with the same contents"""
    app_file_dc = AppFileDataClass(
        circuit=CircuitDataClass(name="c"), shortcuts={"1": "button"}, settings={"a": 1}
    )
    app_file_dc.save(tmp_path / "c.circuit")
    assert AppFileDataClass.load(tmp_path / "c.circuit") == app_file_dc
    circuit_file_dc = CircuitFileDataClass(circuit=CircuitDataClass(name="c"))
    circuit_file_dc.save(tmp_path / "c.json")
    assert CircuitFileDataClass.load(tmp_path / "c.json") == circuit_file_dc


@pytest.mark.parametrize(
    "component_type, settings, message",
    [
        ("digsim.circuit.components.FutureGate", {}, "Unknown component type"),
        ("digsim.future_module.Gate", {}, "Unknown component type"),
        ("NoModule", {}, "Unknown component type"),
        ("builtins.dict", {}, "is not a component"),
        ("digsim.circuit.Circuit", {}, "is not a component"),
        ("digsim.circuit.components.AND", {"ports": 2, "future": 1}, "Invalid settings"),
    ],
)
def test_component_that_cannot_be_created(component_type, settings, message):
    """A component that can't be created gives a DigsimException, the load can continue"""
    component_dc = ComponentDataClass(name="x", type=component_type, settings=settings)
    circuit = Circuit()
    with pytest.raises(DigsimException, match=message):
        component_dc.create(circuit)
    warnings = Circuit().from_dataclass(
        CircuitDataClass(components=[component_dc]), component_exceptions=False
    )
    assert len(warnings) == 1


def test_component_without_display_name():
    """A component stored without display name (older files) keeps its own"""
    component_dc = ComponentDataClass(name="x", type="digsim.circuit.components.AND")
    component = component_dc.create(Circuit())
    assert component.display_name() == "AND"
    component_dc = ComponentDataClass(
        name="y", type="digsim.circuit.components.AND", display_name="My gate"
    )
    assert component_dc.create(Circuit()).display_name() == "My gate"


def test_wire_with_dot_in_component_name(tmp_path):
    """Wires to components with a dot in the name are saved and loaded"""
    circuit = Circuit(name="c")
    button = PushButton(circuit, "button.1")
    led = Led(circuit, "led.v2.0")
    button.O.wire = led.I
    circuit.to_json_file(tmp_path / "c.json")
    loaded = Circuit()
    loaded.from_json_file(tmp_path / "c.json")
    assert loaded.get_component("button.1").O.wired_ports == [loaded.get_component("led.v2.0").I]


def test_wire_shapes_saved_and_loaded(tmp_path):
    """The wire shapes are saved with the circuit file, and are part of the model state"""
    app_file_dc = AppFileDataClass(
        circuit=CircuitDataClass(name="c"),
        wires={"led.I": GuiWireDataClass(path=[150.5, 80, 200])},
    )
    app_file_dc.save(tmp_path / "c.circuit")
    loaded = AppFileDataClass.load(tmp_path / "c.circuit")
    assert loaded.wires == {"led.I": GuiWireDataClass(path=[150.5, 80, 200])}
    assert ModelDataClass.from_app_file_dc(loaded).wires == loaded.wires


def test_circuit_file_without_wire_shapes(tmp_path):
    """Circuit files from older versions, without wire shapes, load as before"""
    filename = tmp_path / "old.circuit"
    filename.write_text('{"circuit": {"name": "c"}, "gui": {}, "shortcuts": {}, "settings": {}}')
    assert AppFileDataClass.load(filename).wires == {}


def test_wire_branches_saved_and_loaded(tmp_path):
    """A wire that starts at a corner of another wire keeps where it starts"""
    wires = {
        "led1.I": GuiWireDataClass(path=[100]),
        "led2.I": GuiWireDataClass(path=[180], branch="led1.I", corner=2),
    }
    app_file_dc = AppFileDataClass(circuit=CircuitDataClass(name="c"), wires=wires)
    app_file_dc.save(tmp_path / "c.circuit")
    loaded = AppFileDataClass.load(tmp_path / "c.circuit")
    assert loaded.wires == wires
    assert loaded.wires["led1.I"].branch is None


def test_positions_saved_as_whole_numbers(tmp_path):
    """Wire positions and component positions are whole numbers, also from older files"""
    filename = tmp_path / "c.circuit"
    filename.write_text(
        '{"circuit": {"name": "c"}, "gui": {"led": {"x": 10.0, "y": 20.0, "z": 0.0}},'
        ' "wires": {"led.I": {"path": [469.5, 175.0, 372.4]}}}'
    )
    loaded = AppFileDataClass.load(filename)
    assert loaded.wires["led.I"].path == [470, 175, 372]
    assert all(isinstance(value, int) for value in loaded.wires["led.I"].path)
    gui = loaded.gui["led"]
    assert (gui.x, gui.y, gui.z) == (10, 20, 0)
    assert isinstance(gui.z, int)
    loaded.save(filename)
    text = filename.read_text()
    assert "469" not in text
    assert ".0" not in text and ".5" not in text
