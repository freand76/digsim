# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Pytest module to test the storage model data classes"""

from digsim.storage_model import AppFileDataClass, CircuitDataClass, ModelDataClass


def test_model_dataclass_keeps_shortcuts():
    """The model state (also used for undo) holds the shortcuts of a loaded file"""
    app_file_dc = AppFileDataClass(circuit=CircuitDataClass(), shortcuts={"1": "button"})
    assert ModelDataClass.from_app_file_dc(app_file_dc).shortcuts == {"1": "button"}
