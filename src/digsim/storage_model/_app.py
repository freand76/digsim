# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""
Module that handles the dataclasses for application
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic.dataclasses import dataclass

from ._circuit import CircuitDataClass, read_json_file, write_json_file


@dataclass
class GuiPositionDataClass:
    x: int = 100
    y: int = 100
    z: int = 0


@dataclass
class AppFileDataClass:
    circuit: CircuitDataClass
    gui: dict[str, GuiPositionDataClass] = Field(default_factory=dict)
    shortcuts: dict[str, str] = Field(default_factory=dict)
    settings: dict[str, Any] = Field(default_factory=dict)

    @staticmethod
    def load(filename: str | Path) -> AppFileDataClass:
        return AppFileDataClass(**read_json_file(filename))

    def save(self, filename: str | Path) -> None:
        write_json_file(filename, self)


@dataclass
class ModelDataClass:
    circuit: CircuitDataClass
    gui: dict[str, GuiPositionDataClass]
    shortcuts: dict[str, str] = Field(default_factory=dict)

    @staticmethod
    def from_app_file_dc(app_file_dc: AppFileDataClass) -> ModelDataClass:
        return ModelDataClass(
            circuit=app_file_dc.circuit, gui=app_file_dc.gui, shortcuts=app_file_dc.shortcuts
        )
