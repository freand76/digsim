# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""Module with the LED component"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from .atoms import CallbackComponent, Component, Parameter, PortIn


if TYPE_CHECKING:
    from digsim.circuit import Circuit


# The colors an LED can have, in the GUI
LED_COLORS = ["red", "green", "blue", "yellow"]


class Led(CallbackComponent):
    """
    An LED, lit while its input is 1.

    Ports:
        I: Input.

    Args:
        circuit: The circuit to add the component to.
        name: The component name, the class name if not given.
        callback: Called with the component when its input changes.
        color: The color of the LED in the GUI: "red", "green", "blue" or "yellow".
    """

    def __init__(
        self,
        circuit: Circuit,
        name: str | None = None,
        callback: Callable[[Component], None] | None = None,
        color: str = "red",
    ) -> None:
        super().__init__(circuit, name, callback)
        self.add_port(PortIn(self, "I"))
        self.parameter_set("color", color)

    @property
    def color(self) -> str:
        """The color of the LED in the GUI"""
        return self.parameter_get("color")

    @property
    def active(self) -> bool:
        return self.I.has_driver() and self.I.value == 1

    @classmethod
    def get_parameters(cls) -> dict[str, Parameter]:
        return {
            "color": {
                "type": "list",
                "items": LED_COLORS,
                "default": "red",
                "description": "Color",
                "reconfigurable": True,
            },
        }
