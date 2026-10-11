# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""
Module for creating a yosys component in the ic folder
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from ._yosys_component import YosysComponent
from .atoms import ComponentException, ParameterValue


if TYPE_CHECKING:
    from digsim.circuit import Circuit


class IntegratedCircuit(YosysComponent):
    """IC component class (predefined yosys module)"""

    def __init__(self, circuit: Circuit, name: str = "IC", ic_name: str | None = None) -> None:
        if ic_name is None:
            raise ComponentException("No IC selected")
        path = f"{self.folder()}/{ic_name}.json"
        super().__init__(circuit, name=name, path=path)
        self.parameter_set("ic_name", ic_name)

    @classmethod
    def folder(cls) -> str:
        """Get predefined IC folder"""
        return str(Path(__file__).parent / "ic")

    def settings_to_dict(self) -> dict[str, ParameterValue]:
        return {"ic_name": self.parameter_get("ic_name")}

    @classmethod
    def get_parameters(cls) -> dict[str, dict[str, Any]]:
        return {
            "ic_name": {
                "type": "ic_name",
                "description": "Select IC",
            }
        }
