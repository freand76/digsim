# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""Pytest module to test CircuitFileDataClass load/save functionality"""

import json
import os

import pytest

from digsim.storage_model._circuit import (
    CircuitDataClass,
    CircuitFileDataClass,
    ComponentDataClass,
    NetDataClass,
    WireDataClass,
)


@pytest.fixture
def sample_circuit_with_wires_dict():
    """Return a minimal valid circuit dict structure."""
    return {
        "circuit": {
            "name": "test_circuit",
            "components": [
                {"name": "and1", "type": "digsim.circuit.components.AND"},
                {"name": "not1", "type": "digsim.circuit.components.NOT"},
            ],
            "wires": [
                {"src": "and1.Y", "dst": "not1.A"},
            ],
        }
    }


@pytest.fixture
def sample_circuit_with_nets_dict():
    """Return a minimal valid circuit dict structure."""
    return {
        "circuit": {
            "name": "test_circuit",
            "components": [
                {"name": "and1", "type": "digsim.circuit.components.AND"},
                {"name": "not1", "type": "digsim.circuit.components.NOT"},
                {"name": "not2", "type": "digsim.circuit.components.NOT"},
            ],
            "nets": [
                {"source": "and1.Y", "sinks": ["not1.A", "not2.A"]},
            ],
        }
    }


@pytest.fixture
def sample_circuit_with_wires_file(tmp_path, sample_circuit_with_wires_dict):
    """Write a sample circuit JSON to a temp file and return the path."""
    filepath = tmp_path / "test_circuit.json"
    with open(filepath, mode="w", encoding="utf-8") as f:
        json.dump(sample_circuit_with_wires_dict, f, indent=4)
    return filepath


@pytest.fixture
def sample_circuit_with_nets_file(tmp_path, sample_circuit_with_nets_dict):
    """Write a sample circuit JSON to a temp file and return the path."""
    filepath = tmp_path / "test_circuit.json"
    with open(filepath, mode="w", encoding="utf-8") as f:
        json.dump(sample_circuit_with_nets_dict, f, indent=4)
    return filepath


class TestCircuitFileDataClassLoad:
    """Tests for CircuitFileDataClass.load()"""

    def test_load_valid_file_with_wires(self, sample_circuit_with_wires_file):
        """Loading a valid JSON file produces a CircuitFileDataClass with correct data."""
        dc = CircuitFileDataClass.load(sample_circuit_with_wires_file)

        assert isinstance(dc, CircuitFileDataClass)
        assert isinstance(dc.circuit, CircuitDataClass)
        assert dc.circuit.name == "test_circuit"

    def test_load_valid_file_with_nets(self, sample_circuit_with_nets_file):
        """Loading a valid JSON file produces a CircuitFileDataClass with correct data."""
        dc = CircuitFileDataClass.load(sample_circuit_with_nets_file)

        assert isinstance(dc, CircuitFileDataClass)
        assert isinstance(dc.circuit, CircuitDataClass)
        assert dc.circuit.name == "test_circuit"

    def test_load_components_with_wires(self, sample_circuit_with_wires_file):
        """Components are correctly deserialized."""
        dc = CircuitFileDataClass.load(sample_circuit_with_wires_file)

        assert len(dc.circuit.components) == 2
        assert all(isinstance(c, ComponentDataClass) for c in dc.circuit.components)
        assert dc.circuit.components[0].name == "and1"
        assert dc.circuit.components[0].type == "digsim.circuit.components.AND"
        assert dc.circuit.components[1].name == "not1"

    def test_load_components_with_nets(self, sample_circuit_with_nets_file):
        """Components are correctly deserialized."""
        dc = CircuitFileDataClass.load(sample_circuit_with_nets_file)

        assert len(dc.circuit.components) == 3
        assert all(isinstance(c, ComponentDataClass) for c in dc.circuit.components)
        assert dc.circuit.components[0].name == "and1"
        assert dc.circuit.components[0].type == "digsim.circuit.components.AND"
        assert dc.circuit.components[1].name == "not1"
        assert dc.circuit.components[2].name == "not2"

    def test_load_wires(self, sample_circuit_with_wires_file):
        """Wires are correctly deserialized."""
        dc = CircuitFileDataClass.load(sample_circuit_with_wires_file)

        assert len(dc.circuit.wires) == 1
        assert isinstance(dc.circuit.wires[0], WireDataClass)
        assert dc.circuit.wires[0].src == "and1.Y"
        assert dc.circuit.wires[0].dst == "not1.A"

    def test_load_nets(self, sample_circuit_with_nets_file):
        """Wires are correctly deserialized."""
        dc = CircuitFileDataClass.load(sample_circuit_with_nets_file)

        assert len(dc.circuit.nets) == 1
        assert isinstance(dc.circuit.nets[0], NetDataClass)
        assert dc.circuit.nets[0].source == "and1.Y"
        assert dc.circuit.nets[0].sinks[0] == "not1.A"
        assert dc.circuit.nets[0].sinks[1] == "not2.A"

    def test_load_component_defaults(self, tmp_path):
        """Components with missing optional fields get default values."""
        data = {
            "circuit": {
                "name": "defaults_test",
                "components": [
                    {"name": "g1", "type": "digsim.circuit.components.NOT"},
                ],
                "wires": [],
            }
        }
        filepath = tmp_path / "defaults.json"
        with open(filepath, mode="w", encoding="utf-8") as f:
            json.dump(data, f)

        dc = CircuitFileDataClass.load(filepath)
        comp = dc.circuit.components[0]
        assert comp.display_name == ""
        assert comp.settings == {}

    def test_load_component_with_settings(self, tmp_path):
        """Components with settings and display_name are correctly loaded."""
        data = {
            "circuit": {
                "name": "settings_test",
                "components": [
                    {
                        "name": "clk1",
                        "type": "digsim.circuit.components.Clock",
                        "display_name": "My Clock",
                        "settings": {"frequency": 1000},
                    },
                ],
                "wires": [],
            }
        }
        filepath = tmp_path / "settings.json"
        with open(filepath, mode="w", encoding="utf-8") as f:
            json.dump(data, f)

        dc = CircuitFileDataClass.load(filepath)
        comp = dc.circuit.components[0]
        assert comp.display_name == "My Clock"
        assert comp.settings == {"frequency": 1000}

    def test_load_file_not_found(self):
        """Loading a non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="File not found"):
            CircuitFileDataClass.load("/nonexistent/path/circuit.json")

    def test_load_malformed_json(self, tmp_path):
        """Loading a file with invalid JSON raises ValueError."""
        filepath = tmp_path / "bad.json"
        filepath.write_text("{invalid json content", encoding="utf-8")

        with pytest.raises(ValueError, match="Malformed JSON file"):
            CircuitFileDataClass.load(str(filepath))

    def test_load_empty_circuit(self, tmp_path):
        """Loading a circuit with no components and no wires works."""
        data = {
            "circuit": {
                "name": "empty",
                "components": [],
                "wires": [],
            }
        }
        filepath = tmp_path / "empty.json"
        with open(filepath, mode="w", encoding="utf-8") as f:
            json.dump(data, f)

        dc = CircuitFileDataClass.load(filepath)
        assert dc.circuit.name == "empty"
        assert dc.circuit.components == []
        assert dc.circuit.wires == []
        assert dc.circuit.nets == []

    def test_load_circuit_default_name(self, tmp_path):
        """Loading a circuit without a name uses the default 'unnamed'."""
        data = {
            "circuit": {
                "components": [],
                "wires": [],
            }
        }
        filepath = tmp_path / "no_name.json"
        with open(filepath, mode="w", encoding="utf-8") as f:
            json.dump(data, f)

        dc = CircuitFileDataClass.load(filepath)
        assert dc.circuit.name == "unnamed"

    def test_load_multiple_wires(self, tmp_path):
        """Loading a circuit with multiple wires works correctly."""
        data = {
            "circuit": {
                "name": "multi_wire",
                "components": [
                    {"name": "btn1", "type": "digsim.circuit.components.PushButton"},
                    {"name": "btn2", "type": "digsim.circuit.components.PushButton"},
                    {"name": "and1", "type": "digsim.circuit.components.AND"},
                    {"name": "led1", "type": "digsim.circuit.components.Led"},
                ],
                "wires": [
                    {"src": "btn1.O", "dst": "and1.A"},
                    {"src": "btn2.O", "dst": "and1.B"},
                    {"src": "and1.Y", "dst": "led1.I"},
                ],
            }
        }
        filepath = tmp_path / "multi_wire.json"
        with open(filepath, mode="w", encoding="utf-8") as f:
            json.dump(data, f)

        dc = CircuitFileDataClass.load(filepath)
        assert len(dc.circuit.wires) == 3
        assert dc.circuit.wires[0].src == "btn1.O"
        assert dc.circuit.wires[2].dst == "led1.I"

    def test_load_multiple_nets(self, tmp_path):
        """Loading a circuit with multiple wires works correctly."""
        data = {
            "circuit": {
                "name": "multi_wire",
                "components": [
                    {"name": "btn1", "type": "digsim.circuit.components.PushButton"},
                    {"name": "btn2", "type": "digsim.circuit.components.PushButton"},
                    {"name": "and1", "type": "digsim.circuit.components.AND"},
                    {"name": "led1", "type": "digsim.circuit.components.Led"},
                ],
                "nets": [
                    {"source": "btn1.O", "sinks": ["and1.A"]},
                    {"source": "btn2.O", "sinks": ["and1.B"]},
                    {"source": "and1.Y", "sinks": ["led1.I"]},
                ],
            }
        }
        filepath = tmp_path / "multi_nets.json"
        with open(filepath, mode="w", encoding="utf-8") as f:
            json.dump(data, f)

        dc = CircuitFileDataClass.load(filepath)
        assert len(dc.circuit.nets) == 3
        assert dc.circuit.nets[0].source == "btn1.O"
        assert dc.circuit.nets[2].sinks[0] == "led1.I"


class TestCircuitFileDataClassSave:
    """Tests for CircuitFileDataClass.save()"""

    def test_save_creates_file(self, tmp_path):
        """Saving a CircuitFileDataClass creates a valid JSON file."""
        circuit_dc = CircuitDataClass(
            name="save_test",
            components=[
                ComponentDataClass(name="g1", type="digsim.circuit.components.NOT"),
            ],
            wires=[],
        )
        dc = CircuitFileDataClass(circuit=circuit_dc)

        filepath = tmp_path / "saved.json"
        dc.save(str(filepath))

        assert filepath.exists()

    def test_save_produces_valid_json(self, tmp_path):
        """Saved file contains valid, parseable JSON."""
        circuit_dc = CircuitDataClass(
            name="json_test",
            components=[],
            wires=[],
        )
        dc = CircuitFileDataClass(circuit=circuit_dc)

        filepath = tmp_path / "valid.json"
        dc.save(str(filepath))

        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)

        assert "circuit" in data
        assert data["circuit"]["name"] == "json_test"

    def test_save_preserves_components(self, tmp_path):
        """Saved file preserves all component data."""
        circuit_dc = CircuitDataClass(
            name="comp_test",
            components=[
                ComponentDataClass(
                    name="and1",
                    type="digsim.circuit.components.AND",
                    display_name="My AND",
                    settings={"key": "value"},
                ),
            ],
            wires=[],
        )
        dc = CircuitFileDataClass(circuit=circuit_dc)

        filepath = tmp_path / "components.json"
        dc.save(str(filepath))

        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)

        comp = data["circuit"]["components"][0]
        assert comp["name"] == "and1"
        assert comp["type"] == "digsim.circuit.components.AND"
        assert comp["display_name"] == "My AND"
        assert comp["settings"] == {"key": "value"}

    def test_save_preserves_wires(self, tmp_path):
        """Saved file preserves all wire data."""
        circuit_dc = CircuitDataClass(
            name="wire_test",
            components=[],
            wires=[
                WireDataClass(src="a.Y", dst="b.A"),
                WireDataClass(src="c.Y", dst="d.B"),
            ],
        )
        dc = CircuitFileDataClass(circuit=circuit_dc)

        filepath = tmp_path / "wires.json"
        dc.save(str(filepath))

        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)

        assert len(data["circuit"]["wires"]) == 2
        assert data["circuit"]["wires"][0] == {"src": "a.Y", "dst": "b.A"}
        assert data["circuit"]["wires"][1] == {"src": "c.Y", "dst": "d.B"}


class TestCircuitFileDataClassRoundTrip:
    """Tests verifying save then load preserves data (round-trip)."""

    def test_roundtrip_full_circuit(self, tmp_path):
        """A save followed by load produces identical data."""
        circuit_dc = CircuitDataClass(
            name="roundtrip_test",
            components=[
                ComponentDataClass(
                    name="btn1",
                    type="digsim.circuit.components.PushButton",
                    display_name="Button 1",
                ),
                ComponentDataClass(
                    name="led1",
                    type="digsim.circuit.components.Led",
                    display_name="LED 1",
                    settings={"color": "red"},
                ),
            ],
            wires=[
                WireDataClass(src="btn1.O", dst="led1.I"),
            ],
        )
        original = CircuitFileDataClass(circuit=circuit_dc)

        filepath = tmp_path / "roundtrip.json"
        original.save(str(filepath))
        loaded = CircuitFileDataClass.load(str(filepath))

        assert loaded.circuit.name == original.circuit.name
        assert len(loaded.circuit.components) == len(original.circuit.components)
        assert len(loaded.circuit.wires) == len(original.circuit.wires)

        for orig_comp, loaded_comp in zip(original.circuit.components, loaded.circuit.components):
            assert loaded_comp.name == orig_comp.name
            assert loaded_comp.type == orig_comp.type
            assert loaded_comp.display_name == orig_comp.display_name
            assert loaded_comp.settings == orig_comp.settings

        for orig_wire, loaded_wire in zip(original.circuit.wires, loaded.circuit.wires):
            assert loaded_wire.src == orig_wire.src
            assert loaded_wire.dst == orig_wire.dst

    def test_roundtrip_empty_circuit(self, tmp_path):
        """Round-trip with an empty circuit preserves defaults."""
        original = CircuitFileDataClass(circuit=CircuitDataClass())

        filepath = tmp_path / "empty_roundtrip.json"
        original.save(str(filepath))
        loaded = CircuitFileDataClass.load(str(filepath))

        assert loaded.circuit.name == "unnamed"
        assert loaded.circuit.components == []
        assert loaded.circuit.wires == []

    def test_roundtrip_overwrite(self, tmp_path):
        """Saving twice to the same file overwrites with latest data."""
        filepath = tmp_path / "overwrite.json"

        first = CircuitFileDataClass(circuit=CircuitDataClass(name="first_version"))
        first.save(str(filepath))

        second = CircuitFileDataClass(circuit=CircuitDataClass(name="second_version"))
        second.save(str(filepath))

        loaded = CircuitFileDataClass.load(str(filepath))
        assert loaded.circuit.name == "second_version"

    def test_load_example_circuit_file(self):
        """Load the existing example_circuit.json file to validate compatibility."""
        example_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "examples",
            "load_save",
            "example_circuit.json",
        )
        if not os.path.exists(example_path):
            pytest.skip("example_circuit.json not found")

        dc = CircuitFileDataClass.load(example_path)

        assert dc.circuit.name == "example_circuit"
        assert len(dc.circuit.components) == 8
        assert len(dc.circuit.nets) == 5
