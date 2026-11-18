# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""
The data of the GUI model: its state, of a loaded file or for undo, and the components
copied to the clipboard
"""

from __future__ import annotations

import json
from dataclasses import asdict

from pydantic import Field
from pydantic.dataclasses import dataclass

from digsim.storage_model import (
    AppFileDataClass,
    CircuitDataClass,
    ComponentDataClass,
    GuiPositionDataClass,
    GuiWireDataClass,
    LineDataClass,
)


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
