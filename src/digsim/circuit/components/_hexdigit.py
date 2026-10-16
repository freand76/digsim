# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""HexDigit component module"""

from __future__ import annotations

import typing
from typing import TYPE_CHECKING

from .atoms import VALUE_TYPE, CallbackComponent, Parameter, PortIn


if TYPE_CHECKING:
    from digsim.circuit import Circuit


class HexDigit(CallbackComponent):
    """
    Hexadecimal digits that show the value of a bus.

    Ports:
        val: Input, 4 bits for each digit. The first digit shows the most significant bits.
        dot: Input, one bit for each decimal point (only with `dot`).

    Args:
        circuit: The circuit to add the component to.
        name: The component name, the class name if not given.
        digits: The number of digits, 1 to 8.
        dot: Add the decimal point input.
    """

    VAL_TO_SEGMENTS: typing.ClassVar = {
        0: "ABCDEF",
        1: "BC",
        2: "ABDEG",
        3: "ABCDG",
        4: "BCFG",
        5: "ACDFG",
        6: "ACDEFG",
        7: "ABC",
        8: "ABCDEFG",
        9: "ABCDFG",
        10: "ABCEFG",
        11: "CDEFG",
        12: "ADEF",
        13: "BCDEG",
        14: "ADEFG",
        15: "AEFG",
    }

    def __init__(
        self, circuit: Circuit, name: str | None = None, digits: int = 1, dot: bool = True
    ) -> None:
        super().__init__(circuit, name)
        self.add_port(PortIn(self, "val", width=4 * digits))
        self.parameter_set("digits", digits)
        self.parameter_set("dot", dot)
        if dot:
            self.add_port(PortIn(self, "dot", width=digits))

    def get_digits(self) -> int:
        """Get the number of digits"""
        return self.parameter_get("digits")

    def value(self) -> VALUE_TYPE:
        """Get value"""
        return self.val.value

    def dot_active(self, digit_id: int = 0) -> bool:
        """Is the dot active for the selected digit_id?"""
        if not self.parameter_get("dot"):
            return False
        dot = self.dot.value
        if dot == "X":
            return False
        dot_value = dot >> (self.dot.width - (digit_id + 1)) & 1
        return dot_value == 1

    def segments(self, digit_id: int = 0) -> str:
        """Which segments are active for the selected digit_id?"""
        value = self.value()
        if value == "X":
            segments = ""
        else:
            digit_value = (value >> (self.val.width - (digit_id + 1) * 4)) & 0xF
            segments = self.VAL_TO_SEGMENTS.get(digit_value, "")
        if self.dot_active(digit_id):
            segments += "."
        return segments

    @classmethod
    def get_parameters(cls) -> dict[str, Parameter]:
        return {
            "digits": {
                "type": "int",
                "min": 1,
                "max": 8,
                "default": 1,
                "description": "Number of digits",
            },
            "dot": {
                "type": "bool",
                "default": False,
                "description": "Use decimal dot",
            },
        }
