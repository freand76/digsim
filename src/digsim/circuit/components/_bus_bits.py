# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Module with the bus/bit <=> bus/bit components"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .atoms import Component, PortMultiBitWire


if TYPE_CHECKING:
    from digsim.circuit import Circuit


class Bus2Wires(Component):
    """Bus to Bits splitter"""

    def __init__(
        self,
        circuit: Circuit,
        name: str | None = None,
        width: int = 1,
        enable: list[int] | None = None,
    ) -> None:
        super().__init__(circuit, name)
        self._bus = PortMultiBitWire(self, "bus", width=width)
        self.add_port(self._bus)
        self._enable = enable if enable is not None else list(range(width))

        for bit_id in range(width):
            if bit_id in self._enable:
                bit_port = self._bus.get_bit(bit_id)
                self.add_port(bit_port)

        self.parameter_set("width", width)
        self.parameter_set("enable", enable)

    @classmethod
    def get_parameters(cls) -> dict[str, dict[str, Any]]:
        return {
            "width": {
                "type": "int",
                "min": 2,
                "max": 32,
                "default": 2,
                "description": "Bus width",
            },
            "enable": {
                "type": "width_bool",
                "default": None,
                "description": "Enable bit",
            },
        }


class Wires2Bus(Component):
    """Bits to Bus merger"""

    def __init__(self, circuit: Circuit, name: str | None = None, width: int = 1) -> None:
        super().__init__(circuit, name)
        self._bus = PortMultiBitWire(self, "bus", width=width, output=True)
        self.add_port(self._bus)
        for bit_id in range(width):
            bit_port = self._bus.get_bit(bit_id)
            self.add_port(bit_port)
        self.parameter_set("width", width)

    @classmethod
    def get_parameters(cls) -> dict[str, dict[str, Any]]:
        return {
            "width": {
                "type": "int",
                "min": 2,
                "max": 32,
                "default": 2,
                "description": "Bus width",
            },
        }
