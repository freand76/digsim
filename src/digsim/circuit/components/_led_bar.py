# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Module with the LED bar component"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .atoms import CallbackComponent, Parameter, PortIn


if TYPE_CHECKING:
    from digsim.circuit import Circuit


class LedBar(CallbackComponent):
    """
    A row of LEDs showing the bits of a bus.

    Ports:
        I: Input, `width` bits.

    Args:
        circuit: The circuit to add the component to.
        name: The component name, the class name if not given.
        width: The number of LEDs, 1 to 16.
    """

    def __init__(self, circuit: Circuit, name: str | None = None, width: int = 8) -> None:
        super().__init__(circuit, name, callback=None)
        self.add_port(PortIn(self, "I", width=width))
        self.parameter_set("width", width)

    def lit(self) -> list[bool]:
        """The state of each LED, bit 0 first"""
        width = self.parameter_get("width")
        value = self.I.value
        if not isinstance(value, int):
            return [False] * width
        return [bool((value >> bit) & 1) for bit in range(width)]

    @classmethod
    def get_parameters(cls) -> dict[str, Parameter]:
        return {
            "width": {
                "type": "int",
                "min": 1,
                "max": 16,
                "default": 8,
                "description": "Number of LEDs",
            },
        }
