# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""Pytest module to test the state of the GUI model"""

from digsim.app._model_data import ModelDataClass
from digsim.storage_model import (
    AppFileDataClass,
    CircuitDataClass,
    GuiPositionDataClass,
    GuiWireDataClass,
    LineDataClass,
)


def test_model_state_of_a_loaded_file():
    """The model state (also used for undo) holds what a loaded file has"""
    line = LineDataClass(ports=["B.O", "L.I"], segments=[["B.O", "L.I"]])
    app_file_dc = AppFileDataClass(
        circuit=CircuitDataClass(name="c"),
        gui={"B": GuiPositionDataClass(x=10, y=20)},
        lines=[line],
        wires={"L.I": GuiWireDataClass(path=[150, 80, 200])},
        shortcuts={"1": "B"},
    )
    model_dc = ModelDataClass.from_app_file_dc(app_file_dc)
    assert model_dc.circuit == app_file_dc.circuit
    assert model_dc.gui == {"B": GuiPositionDataClass(x=10, y=20)}
    assert model_dc.lines == [line]
    assert model_dc.wires == {"L.I": GuiWireDataClass(path=[150, 80, 200])}
    assert model_dc.shortcuts == {"1": "B"}
