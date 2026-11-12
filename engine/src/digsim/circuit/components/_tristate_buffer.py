# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Module with the tristate buffer component"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .atoms import Component, Parameter, PortIn, PortOutDelta


if TYPE_CHECKING:
    from digsim.circuit import Circuit


class TristateBuffer(Component):
    """
    A tristate buffer: drives its input to its output while enabled, and does not drive
    it at all ("Z", high impedance) otherwise. Several outputs can drive the same wire,
    like the outputs of the chips on a bus. The one that is enabled drives it, and if more
    than one drives different values, the value is undefined ("X").

    Ports:
        A: Input, `width` bits.
        OE: Output enable input, active high (or low, with active_low=True).
        Y: Tristate output, `width` bits.

    Args:
        circuit: The circuit to add the component to.
        name: The component name, the class name if not given.
        width: The number of bits.
        active_low: The output is enabled when OE is low.
    """

    def __init__(
        self,
        circuit: Circuit,
        name: str | None = None,
        width: int = 1,
        active_low: bool = False,
    ) -> None:
        super().__init__(circuit, name)
        self.add_port(PortIn(self, "A", width=width))
        self.add_port(PortIn(self, "OE"))
        output = PortOutDelta(self, "Y", width=width)
        output.set_tristate()
        self.add_port(output)
        self._enable_level = 0 if active_low else 1
        self.parameter_set("width", width)
        self.parameter_set("active_low", active_low)

    def default_state(self) -> None:
        self.Y.value = "Z"

    def update(self) -> None:
        enable = self.OE.value
        if enable == self._enable_level:
            self.Y.value = self.A.value
        elif isinstance(enable, int):
            self.Y.value = "Z"
        else:
            # An undefined enable: it may drive the wire or not
            self.Y.value = "X"

    @classmethod
    def get_parameters(cls) -> dict[str, Parameter]:
        return {
            "width": {
                "type": "int",
                "min": 1,
                "max": 32,
                "default": 1,
                "description": "Bus width",
            },
            "active_low": {
                "type": "bool",
                "default": False,
                "description": "Output enable active low",
            },
        }
