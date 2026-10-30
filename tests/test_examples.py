# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""Pytest module to test the example circuits of File > Examples"""

import json
from pathlib import Path

import pytest

from digsim.app._examples import Example, copy_example, example_circuits, examples_folder
from digsim.circuit import Circuit
from digsim.circuit.components import SubCircuit


# Also on the other platforms: the minimal scope of the tests (see .github/workflows)
pytestmark = pytest.mark.sanity

ROOT = Path(__file__).parent.parent


# The build outputs that setup.py leaves out of the package
BUILD_OUTPUTS = {".elf", ".lst", ".hex", ".o", ".map"}


def _files(folder: Path) -> set[str]:
    return {
        path.relative_to(folder).as_posix()
        for path in folder.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix not in BUILD_OUTPUTS
    }


def test_examples_are_packaged():
    """The package digsim.examples has the files of circuits/ (setup.py maps it)"""
    assert _files(examples_folder()) == _files(ROOT / "circuits")
    assert "rv32e/rv32e_code/lcd.bin" in _files(examples_folder())


def test_example_circuits():
    """Each circuit of the folders, without the subcircuits of another one"""
    titles = [example.title for example in example_circuits()]
    assert titles == sorted(titles, key=str.lower)
    assert "rv32e_demo" in titles
    assert "adder_4bit" in titles
    assert "counter_yosys_netlist" in titles
    assert "counter_yosys_verilog" in titles
    for subcircuit in ("cpu", "timer", "full_adder"):
        assert subcircuit not in titles


def test_example_circuits_left_out(tmp_path):
    """A subcircuit is left out, a file that isn't a circuit doesn't stop the list"""
    folder = tmp_path / "example"
    folder.mkdir()
    (folder / "top.circuit").write_text(
        json.dumps(
            {
                "circuit": {
                    "components": [
                        {
                            "name": "part",
                            "type": "digsim.circuit.components.SubCircuit",
                            "settings": {"path": "part.circuit"},
                        }
                    ]
                }
            }
        )
    )
    (folder / "part.circuit").write_text(json.dumps({"circuit": {"components": []}}))
    (folder / "broken.circuit").write_text("not json")
    titles = [example.title for example in example_circuits(tmp_path)]
    assert titles == ["broken", "top"]


def test_copy_example(tmp_path):
    """The folder of the example is copied, a new one each time, and its circuit loads"""
    example = Example(examples_folder() / "subcircuits" / "adder_4bit.circuit")
    path = copy_example(example, tmp_path)
    assert path == tmp_path / "subcircuits" / "adder_4bit.circuit"
    assert sorted(file.name for file in path.parent.iterdir()) == [
        "adder_4bit.circuit",
        "full_adder.circuit",
        "half_adder.circuit",
    ]
    again = copy_example(example, tmp_path)
    assert again == tmp_path / "subcircuits_2" / "adder_4bit.circuit"
    assert copy_example(example, tmp_path).parent.name == "subcircuits_3"
    circuit = Circuit()
    circuit.from_json_file(str(again))
    parts = [c for c in circuit.get_toplevel_components() if isinstance(c, SubCircuit)]
    assert len(parts) == 4
