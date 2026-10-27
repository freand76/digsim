# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""
Module that handles the dataclasses for application
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic.dataclasses import dataclass

from ._circuit import (
    CircuitDataClass,
    ComponentDataClass,
    LineDataClass,
    read_json_file,
    write_json_file,
)


@dataclass
class GuiPositionDataClass:
    x: int = 100
    y: int = 100
    z: int = 0


@dataclass
class GuiWireDataClass:
    """
    The shape of a wire in the GUI: the position of each segment between the first and
    the last, [x, y, x, ..., x], see digsim.app._wire_path. A wire that starts at a
    corner of another wire from the same output port (a branch, see digsim.app._wire_tree)
    has that wire, by the input port it drives, and the number of the corner. A wire that
    ends at a corner of another wire (it joins its line, see digsim.app._wire_lines) has
    that wire and corner as its joint. A connection that is not drawn, but implied by the
    line that its ports are on, is not 'drawn'.
    """

    path: list[int]
    branch: str | None = None
    corner: int | None = None
    joint: str | None = None
    joint_corner: int | None = None
    drawn: bool = True

    @field_validator("path", mode="before")
    @classmethod
    def _whole_numbers(cls, path: Any) -> Any:
        """Positions are whole numbers, files with fractions are rounded"""
        if isinstance(path, list):
            return [round(value) if isinstance(value, float) else value for value in path]
        return path


@dataclass
class AppFileDataClass:
    """
    A GUI circuit file: the components, their positions, and the lines of wires that
    connect them (see LineDataClass). Files from before lines have the connections in
    'circuit' and the shapes of the wires in 'wires'.
    """

    circuit: CircuitDataClass
    gui: dict[str, GuiPositionDataClass] = Field(default_factory=dict)
    lines: list[LineDataClass] = Field(default_factory=list)
    # The wire shapes of files from before lines, by the input port each wire drives
    wires: dict[str, GuiWireDataClass] = Field(default_factory=dict)
    shortcuts: dict[str, str] = Field(default_factory=dict)
    settings: dict[str, Any] = Field(default_factory=dict)

    @staticmethod
    def load(filename: str | Path) -> AppFileDataClass:
        return AppFileDataClass(**read_json_file(filename))

    def save(self, filename: str | Path) -> None:
        data = asdict(self)
        # Not in files with lines, the lines have the connections and the wires
        if not self.wires:
            del data["wires"]
        if not self.circuit.wires:
            del data["circuit"]["wires"]
        write_json_file(filename, data)


@dataclass
class ModelDataClass:
    """
    The state of the GUI model, of a loaded file or for undo. The undo states have the
    wires as the model knows them ('wires'), loaded files have lines or wires.
    """

    circuit: CircuitDataClass
    gui: dict[str, GuiPositionDataClass]
    shortcuts: dict[str, str] = Field(default_factory=dict)
    wires: dict[str, GuiWireDataClass] = Field(default_factory=dict)
    lines: list[LineDataClass] = Field(default_factory=list)

    @staticmethod
    def from_app_file_dc(app_file_dc: AppFileDataClass) -> ModelDataClass:
        return ModelDataClass(
            circuit=app_file_dc.circuit,
            gui=app_file_dc.gui,
            shortcuts=app_file_dc.shortcuts,
            wires=app_file_dc.wires,
            lines=app_file_dc.lines,
        )


@dataclass
class ClipboardDataClass:
    """
    Components copied in the GUI, with their positions and the lines between them (only
    their own ports). File paths in the settings, like a Verilog file, are absolute, so
    that they can be pasted in another circuit.
    """

    components: list[ComponentDataClass] = Field(default_factory=list)
    gui: dict[str, GuiPositionDataClass] = Field(default_factory=dict)
    lines: list[LineDataClass] = Field(default_factory=list)
    # Marks the text as DigSim components, other text on the clipboard isn't pasted
    digsim_clipboard: int = 1

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @staticmethod
    def from_json(text: str) -> ClipboardDataClass | None:
        """The components of a text, None if it isn't DigSim components"""
        try:
            data = json.loads(text)
        except ValueError:
            return None
        if not isinstance(data, dict) or data.get("digsim_clipboard") != 1:
            return None
        try:
            return ClipboardDataClass(**data)
        except (TypeError, ValueError):
            # Not valid: pydantic's ValidationError is a ValueError
            return None
