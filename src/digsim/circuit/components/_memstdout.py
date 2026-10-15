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
    """
    Prints the characters written to one address, like a memory-mapped terminal.
    A newline (0x0A) prints the whole line.

    Ports:
        clk: Clock input.
        Address: Input, 16 bits.
        DataIn: Input, 8 bits.
        WE: Write enable input.

    Args:
        circuit: The circuit to add the component to.
        address: The address to print the characters written to.
    """

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
        if self.WE.value != 1 or self.Address.value != self._address:
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
