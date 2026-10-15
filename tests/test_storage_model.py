# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Pytest module to test the storage model data classes"""

import pytest

from digsim.circuit import Circuit
from digsim.circuit.components.atoms import DigsimException
from digsim.storage_model import (
    AppFileDataClass,
    CircuitDataClass,
    CircuitFileDataClass,
    ComponentDataClass,
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
