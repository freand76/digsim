# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""
This module implements a synchronous memory mapped stdout output
with 8-bit memory bus and 16-bit address bus.
The address is listens to can be changed with the 'address' parameter.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from digsim.circuit.components.atoms import Component, PortIn, PortWire


if TYPE_CHECKING:
    from digsim.circuit import Circuit


class MemStdOut(Component):
    """Synchronous memory mapped stdout class"""

    def __init__(self, circuit: Circuit, address: int = 0x8000) -> None:
        super().__init__(circuit, "MemStdOut")
        self._address = address
        self.add_port(PortIn(self, "clk"))
        self.add_port(PortWire(self, "Address", width=16))
        self.add_port(PortWire(self, "DataIn", width=8))
        self.add_port(PortWire(self, "WE"))
        self._str = ""

    def update(self) -> None:
        rising_edge = self.clk.is_rising_edge()
        if self.WE.value == 0 or self.Address.value != self._address:
            return
        if rising_edge:
            datain = self.DataIn.value
            if datain == "X":
                return
            if datain == 0x0A:
                print(f"StringOutput [line]: '{self._str}'")
                self._str = ""
            else:
                inchar = chr(datain)
                print(f"StringOutput [char]: '{inchar}'")
                self._str += inchar
