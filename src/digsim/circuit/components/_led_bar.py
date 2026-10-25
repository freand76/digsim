# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""Module with the LED bar component"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ._led import LED_COLORS
from .atoms import CallbackComponent, Parameter, PortIn


if TYPE_CHECKING:
    from digsim.circuit import Circuit


class LedBar(CallbackComponent):
    """
    A column of LEDs, with one input for each LED.

    Ports:
        0, 1, ...: Inputs, one for each LED, numbered from 0.

    Args:
        circuit: The circuit to add the component to.
        name: The component name, the class name if not given.
        width: The number of LEDs, 1 to 16.
        color: The color of the LEDs in the GUI: "red", "green", "blue" or "yellow".
    """

    def __init__(
        self, circuit: Circuit, name: str | None = None, width: int = 8, color: str = "red"
    ) -> None:
        super().__init__(circuit, name, callback=None)
        for bit in range(width):
            self.add_port(PortIn(self, f"{bit}"))
        self.parameter_set("width", width)
        self.parameter_set("color", color)

    @property
    def color(self) -> str:
        """The color of the LEDs in the GUI"""
        return self.parameter_get("color")

    def lit(self) -> list[bool]:
        """The state of each LED, LED 0 first"""
        return [port.value == 1 for port in self.inports()]

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
            "color": {
                "type": "list",
                "items": LED_COLORS,
                "default": "red",
                "description": "Color",
                "reconfigurable": True,
            },
        }
