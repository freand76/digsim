# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Pytest module to test the storage model data classes"""

import pytest

from digsim.storage_model import (
    AppFileDataClass,
    CircuitDataClass,
    CircuitFileDataClass,
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
