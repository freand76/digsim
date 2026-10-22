# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""
Module for creating a yosys component in the ic folder
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from ._yosys_component import YosysComponent
from .atoms import ComponentException, Parameter, ParameterValue


if TYPE_CHECKING:
    from digsim.circuit import Circuit


# A short description of each bundled IC, for the IC selector of the GUI
IC_DESCRIPTIONS = {
    "4017": "Decade counter with 10 decoded outputs",
    "4511": "BCD to 7-segment latch, decoder and driver",
    "7448": "BCD to 7-segment decoder",
    "7485": "4-bit magnitude comparator",
    "74138": "3-to-8 line decoder, demultiplexer (demux)",
    "74151": "8-to-1 multiplexer (mux), data selector",
    "74162": "Synchronous decade counter with parallel load",
    "74181": "4-bit arithmetic logic unit (ALU)",
    "74182": "Look-ahead carry generator for the 74181",
    "74193": "Up/down binary counter with parallel load",
    "74194": "4-bit bidirectional universal shift register",
    "74283": "4-bit binary full adder",
    "74595": "8-bit shift register with output register",
}


class IntegratedCircuit(YosysComponent):
    """
    A classic logic chip, from the Yosys netlists in digsim/circuit/components/ic. It is
    named after the netlist's module, like ttl_74162.

    Ports:
        The ports of the chip.

    Args:
        circuit: The circuit to add the component to.
        ic_name: The netlist's file name without .json, like "74162" or "7448".
    """

    def __init__(self, circuit: Circuit, ic_name: str | None = None) -> None:
        if ic_name is None:
            raise ComponentException("No IC selected")
        path = f"{self.folder()}/{ic_name}.json"
        super().__init__(circuit, path=path)
        self.parameter_set("ic_name", ic_name)

    @classmethod
    def folder(cls) -> str:
        """Get predefined IC folder"""
        return str(Path(__file__).parent / "ic")

    @classmethod
    def available(cls) -> dict[str, str]:
        """The ICs in the IC folder, with their descriptions (empty if there is none)"""
        return {
            path.stem: IC_DESCRIPTIONS.get(path.stem, "")
            for path in sorted(Path(cls.folder()).glob("*.json"))
        }

    def settings_to_dict(self) -> dict[str, ParameterValue]:
        return {"ic_name": self.parameter_get("ic_name")}

    @classmethod
    def get_parameters(cls) -> dict[str, Parameter]:
        return {
            "ic_name": {
                "type": "ic_name",
                "description": "Select IC",
            }
        }
