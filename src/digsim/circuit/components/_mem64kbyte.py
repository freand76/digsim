# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""
This module implements a 64kByte synchronous memory
with 8-bit memory bus and 16-bit address bus.
It cam be prefilled with binary data from 'rom_filename'
starting at 'rom_address'.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from digsim.circuit.components.atoms import (
    VALUE_TYPE,
    Component,
    PortIn,
    PortOutDelta,
    PortWire,
)


if TYPE_CHECKING:
    from pathlib import Path

    from digsim.circuit import Circuit


class Mem64kByte(Component):
    """
    A 64 kB memory, read or written on a rising clock edge. It is always named Memory.

    Ports:
        clk: Clock input.
        Address: Input, 16 bits.
        DataIn: Input, 8 bits.
        WE: Write enable input, 1 writes DataIn, otherwise DataOut is read.
        DataOut: Output, 8 bits.

    Args:
        circuit: The circuit to add the component to.
        rom_filename: A binary file loaded into the memory when it is created.
        rom_address: The address to load the file at.
    """

    def __init__(
        self, circuit: Circuit, rom_filename: str | Path | None = None, rom_address: int = 0
    ) -> None:
        super().__init__(circuit, "Memory")
        self.add_port(PortIn(self, "clk"))
        self.add_port(PortWire(self, "Address", width=16))
        self.add_port(PortWire(self, "DataIn", width=8))
        self.add_port(PortWire(self, "WE"))
        self.add_port(PortOutDelta(self, "DataOut", width=8))
        self._mem_array: list[VALUE_TYPE] = [0] * 65536
        if rom_filename is not None:
            with open(rom_filename, mode="rb") as rom:
                romdata = rom.read()
                for idx, byte in enumerate(romdata):
                    self._mem_array[rom_address + idx] = byte

    def update(self) -> None:
        rising_edge = self.clk.is_rising_edge()
        if not rising_edge or self.Address.value == "X":
            return
        addr = self.Address.value
        assert isinstance(addr, int)
        we = self.WE.value
        if we == 1:
            datain = self.DataIn.value
            self._mem_array[addr] = datain
        else:
            dataout = self._mem_array[addr]
            self.DataOut.value = dataout
