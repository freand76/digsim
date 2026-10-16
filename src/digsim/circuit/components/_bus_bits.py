# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Module with the bus/bit <=> bus/bit components"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .atoms import Component, Parameter, PortMultiBitWire


if TYPE_CHECKING:
    from digsim.circuit import Circuit


class Bus2Wires(Component):
    """
    Splits a bus into single-bit wires.

    Ports:
        bus: Input, `width` bits.
        bus_0, bus_1, ...: Outputs, one for each enabled bit. bus_0 is the least significant bit.

    Args:
        circuit: The circuit to add the component to.
        name: The component name, the class name if not given.
        width: The number of bits.
        enable: The bits to have outputs for, all if None.
    """

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
    def get_parameters(cls) -> dict[str, Parameter]:
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
    """
    Merges single-bit wires into a bus.

    Ports:
        bus_0, bus_1, ...: Inputs, one for each bit. bus_0 is the least significant bit.
        bus: Output, `width` bits.

    Args:
        circuit: The circuit to add the component to.
        name: The component name, the class name if not given.
        width: The number of bits.
    """

    def __init__(self, circuit: Circuit, name: str | None = None, width: int = 1) -> None:
        super().__init__(circuit, name)
        self._bus = PortMultiBitWire(self, "bus", width=width, output=True)
        self.add_port(self._bus)
        for bit_id in range(width):
            bit_port = self._bus.get_bit(bit_id)
            self.add_port(bit_port)
        self.parameter_set("width", width)

    @classmethod
    def get_parameters(cls) -> dict[str, Parameter]:
        return {
            "width": {
                "type": "int",
                "min": 2,
                "max": 32,
                "default": 2,
                "description": "Bus width",
            },
        }
