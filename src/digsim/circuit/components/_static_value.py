# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Module with the Static Leve component"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .atoms import Component, Parameter, PortOutImmediate


if TYPE_CHECKING:
    from digsim.circuit import Circuit


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
    """

    def __init__(
        self, circuit: Circuit, name: str | None = None, width: int = 1, value: int = 0
    ) -> None:
        super().__init__(circuit, name)
        self.parameter_set("width", width)
        self.parameter_set("value", value)
        self.add_port(PortOutImmediate(self, "O", width=width))

    def default_state(self) -> None:
        self.O.value = self.parameter_get("value")

    def reconfigure(self) -> None:
        self.O.value = self.parameter_get("value")

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
        }
