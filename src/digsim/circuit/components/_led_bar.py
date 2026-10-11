# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Module with the LED bar component"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .atoms import CallbackComponent, PortIn


if TYPE_CHECKING:
    from digsim.circuit import Circuit


class LedBar(CallbackComponent):
    """A row of LEDs showing the bits of a bus"""

    def __init__(self, circuit: Circuit, name: str | None = None, width: int = 8) -> None:
        super().__init__(circuit, name, callback=None)
        self.add_port(PortIn(self, "I", width=width))
        self.parameter_set("width", width)

    def lit(self) -> list[bool]:
        """The state of each LED, bit 0 first"""
        width = self.parameter_get("width")
        value = self.I.value
        if value == "X":
            return [False] * width
        return [bool((value >> bit) & 1) for bit in range(width)]

    @classmethod
    def get_parameters(cls) -> dict[str, dict[str, Any]]:
        return {
            "width": {
                "type": "int",
                "min": 1,
                "max": 16,
                "default": 8,
                "description": "Number of LEDs",
            },
        }
