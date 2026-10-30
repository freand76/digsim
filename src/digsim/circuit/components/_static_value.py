# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""Module with the Static Leve component"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .atoms import Component, ComponentException, Parameter, PortOutImmediate


if TYPE_CHECKING:
    from digsim.circuit import Circuit

STATIC_VALUE_RADIXES = ["dec", "hex", "bin"]


class StaticValue(Component):
    """
    A constant value on a wire or a bus.

    Ports:
        O: Output, `width` bits.

    Args:
        circuit: The circuit to add the component to.
        name: The component name, the class name if not given.
        width: The number of bits, 1 to 16.
        value: The value.
        radix: How the value is shown in the GUI: "dec", "hex" or "bin".
    """

    def __init__(
        self,
        circuit: Circuit,
        name: str | None = None,
        width: int = 1,
        value: int = 0,
        radix: str = "dec",
    ) -> None:
        super().__init__(circuit, name)
        if radix not in STATIC_VALUE_RADIXES:
            raise ComponentException(f"Unknown radix '{radix}', use one of {STATIC_VALUE_RADIXES}")
        self.parameter_set("width", width)
        self.parameter_set("value", value)
        self.parameter_set("radix", radix)
        self.add_port(PortOutImmediate(self, "O", width=width))

    def default_state(self) -> None:
        self.O.value = self.parameter_get("value")

    def reconfigure(self) -> None:
        self.O.value = self.parameter_get("value")

    def text(self) -> str:
        """
        The value as text, in the radix: hexadecimal (0x) and binary (0b) with all digits
        for the width. A single bit is 0 or 1.
        """
        value = self.parameter_get("value")
        width = self.parameter_get("width")
        radix = self.parameter_get("radix")
        if width == 1 or radix == "dec":
            return str(value)
        if radix == "bin":
            return f"0b{value:0{width}b}"
        return f"0x{value:0{(width + 3) // 4}X}"

    @property
    def active(self) -> bool:
        return self.parameter_get("width") == 1 and self.parameter_get("value") == 1

    @classmethod
    def get_parameters(cls) -> dict[str, Parameter]:
        return {
            "value": {
                "type": "width_pow2",
                "default": 0,
                "description": "Static value",
                "reconfigurable": True,
            },
            "width": {
                "type": "int",
                "min": 1,
                "max": 16,
                "default": 1,
                "description": "Static value bitwidth",
            },
            "radix": {
                "type": "list",
                "items": STATIC_VALUE_RADIXES,
                "default": "dec",
                "description": "Show the value as",
                "reconfigurable": True,
            },
        }
