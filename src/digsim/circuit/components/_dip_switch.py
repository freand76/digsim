# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""A Dip-switch component"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .atoms import CallbackComponent, PortOutImmediate


if TYPE_CHECKING:
    from digsim.circuit import Circuit


class DipSwitch(CallbackComponent):
    """On/Off Switch  component class"""

    def __init__(self, circuit: Circuit, name: str | None = None, bits: int = 8) -> None:
        super().__init__(circuit, name)
        self._bits = bits
        self.parameter_set("bits", bits)
        self._select: int | None = None
        for index in range(self._bits):
            portout = PortOutImmediate(self, f"{index}")
            self.add_port(portout)

    def bits(self) -> int:
        """Get number of bits in dipswitch"""
        return self._bits

    def is_set(self, bit: int) -> bool:
        """Test if dip switch bit is set"""
        return self.port(f"{bit}").value == 1

    def default_state(self) -> None:
        for port in self.outports():
            port.value = 0

    def select(self, idx: int | None) -> None:
        """Select bit in dipswitch (for toggle)"""
        self._select = idx

    def selected(self) -> int | None:
        """Get selected bit in dipswitch (for gui)"""
        return self._select

    def _toggle_bit(self, bit: int) -> None:
        if bit >= self._bits:
            return
        port = self.port(f"{bit}")
        if port.value == 1:
            port.value = 0
        else:
            port.value = 1

    def toggle(self) -> None:
        """Toggle the switch"""
        if self._select is None:
            return
        self._toggle_bit(self._select)

    def onpress(self) -> None:
        self.toggle()

    @property
    def has_action(self) -> bool:
        return True

    @classmethod
    def get_parameters(cls) -> dict[str, dict[str, Any]]:
        return {
            "bits": {
                "type": "int",
                "min": 2,
                "max": 8,
                "default": 8,
                "description": "Number of bits",
            },
        }
