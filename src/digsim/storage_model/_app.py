# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""
Module that handles the dataclasses for application
"""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from pydantic import Field
from pydantic.dataclasses import dataclass

from ._circuit import CircuitDataClass


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
    def load(filename):
        try:
            with open(filename, mode="r", encoding="utf-8") as json_file:
                app_filedata_class = AppFileDataClass(**json.load(json_file))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Malformed JSON file: {filename} - {exc}") from exc
        except FileNotFoundError as exc:
            raise FileNotFoundError(f"File not found: {filename}") from exc
        return app_filedata_class

    def save(self, filename):
        json_object = json.dumps(asdict(self), indent=4)
        with open(filename, mode="w", encoding="utf-8") as json_file:
            json_file.write(json_object)


@dataclass
class ModelDataClass:
    circuit: CircuitDataClass
    gui: dict[str, GuiPositionDataClass]

    @staticmethod
    def from_app_file_dc(app_file_dc):
        return ModelDataClass(circuit=app_file_dc.circuit, gui=app_file_dc.gui)
