# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""Pytest module to test the storage model data classes"""

import json

import pytest

from digsim.circuit import Circuit
from digsim.circuit.components import Led, PushButton
from digsim.circuit.components.atoms import DigsimException
from digsim.storage_model import (
    AppFileDataClass,
    CircuitDataClass,
    CircuitFileDataClass,
    ComponentDataClass,
    GuiPositionDataClass,
    GuiWireDataClass,
    LineDataClass,
    ModelDataClass,
)
from digsim.storage_model._circuit import JSON_WIDTH, json_text


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


def test_rotation_saved_only_for_rotated_components(tmp_path):
    """Files of circuits without rotated components stay as they were"""
    app_file_dc = AppFileDataClass(
        circuit=CircuitDataClass(name="c"),
        gui={
            "a": GuiPositionDataClass(x=10, y=20),
            "b": GuiPositionDataClass(rotation=90, flipped=True),
        },
    )
    app_file_dc.save(tmp_path / "c.circuit")
    gui = json.loads((tmp_path / "c.circuit").read_text())["gui"]
    assert "rotation" not in gui["a"] and "flipped" not in gui["a"]
    assert (gui["b"]["rotation"], gui["b"]["flipped"]) == (90, True)
    loaded = AppFileDataClass.load(tmp_path / "c.circuit")
    assert (loaded.gui["a"].rotation, loaded.gui["b"].rotation) == (0, 90)
    assert (loaded.gui["a"].flipped, loaded.gui["b"].flipped) == (False, True)


def test_line_connects_its_ports():
    """Each output port of a line drives each input port of it"""
    circuit = Circuit(name="c")
    buttons = [PushButton(circuit, f"B{i}") for i in range(2)]
    leds = [Led(circuit, f"L{i}") for i in range(2)]
    line = LineDataClass(ports=["B0.O", "L0.I", "B1.O", "L1.I"])
    line.connect(circuit)
    for button in buttons:
        assert button.O.wired_ports == [led.I for led in leds]
    # Again: nothing more
    line.connect(circuit)
    assert len(leds[0].I.get_drivers()) == 2


def test_line_connects_the_ports_that_are_there():
    """
    A port that is missing (its component couldn't be loaded) is an error, and the
    other ports of the line are connected. Without a list of errors, it is raised.
    """
    circuit = Circuit(name="c")
    buttons = [PushButton(circuit, f"B{i}") for i in range(2)]
    led = Led(circuit, "L0")
    line = LineDataClass(ports=["B0.O", "Gone.I", "L0.I", "B1.O"])
    errors: list[str] = []
    line.connect(circuit, errors)
    assert len(errors) == 1 and "Gone" in errors[0]
    for button in buttons:
        assert button.O.wired_ports == [led.I]
    with pytest.raises(DigsimException):
        line.connect(circuit)


def test_circuit_file_with_lines(tmp_path):
    """
    A GUI circuit file has its connections in its lines: no list of wires, and no wire
    shapes of the old format. A Python circuit loads it with its connections.
    """
    line = LineDataClass(
        ports=["B.O", "L.I"], points={"1": [150, 100]}, segments=[["B.O", "1"], ["1", "L.I"]]
    )
    app_file_dc = AppFileDataClass(circuit=CircuitDataClass(name="c"), lines=[line])
    app_file_dc.circuit.components = [
        ComponentDataClass(name="B", type="digsim.circuit.components.PushButton"),
        ComponentDataClass(name="L", type="digsim.circuit.components.Led"),
    ]
    filename = tmp_path / "c.circuit"
    app_file_dc.save(filename)
    saved = json.loads(filename.read_text())
    assert "wires" not in saved
    assert "wires" not in saved["circuit"]
    assert AppFileDataClass.load(filename) == app_file_dc
    assert ModelDataClass.from_app_file_dc(app_file_dc).lines == [line]
    circuit = Circuit()
    circuit.from_json_file(filename)
    assert circuit.get_component("B").O.wired_ports == [circuit.get_component("L").I]


def test_compact_json_text():
    """A circuit file is compact: what fits on a line is on one line"""
    data = {"name": "c", "point": [10, 20], "nested": {"a": [1, 2], "b": "text"}}
    assert json_text(data) == json.dumps(data)
    lines = {"segments": [[f"Component_{i}.O", str(i)] for i in range(20)], "ports": []}
    text = json_text(lines)
    assert json.loads(text) == lines
    assert all(len(line) <= JSON_WIDTH for line in text.splitlines())
    # The short items of a long list fill the lines, a fraction of json.dumps(indent=4)
    assert len(text.splitlines()) * 5 < len(json.dumps(lines, indent=4).splitlines())
    # Objects in a list are one on each line, or on one line if they fit
    objects = [{"x": i, "text": "a" * 40} for i in range(3)]
    assert json.loads(json_text(objects)) == objects
