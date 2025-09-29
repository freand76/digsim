# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""
This module implements a 64kByte synchronous memory
with 8-bit memory bus and 16-bit address bus.
It cam be prefilled with binary data from 'rom_filename'
starting at 'rom_address'.
"""

from digsim.circuit.components.atoms import Component, PortIn, PortOutDelta, PortWire


class Mem64kByte(Component):
    """64kByte synchronous memory class"""

    def __init__(self, circuit, rom_filename=None, rom_address=0):
        super().__init__(circuit, "Memory")
        self.add_port(PortIn(self, "clk"))
        self.add_port(PortWire(self, "Address", width=16))
        self.add_port(PortWire(self, "DataIn", width=8))
        self.add_port(PortWire(self, "WE"))
        self.add_port(PortOutDelta(self, "DataOut", width=8))
        self._mem_array = [0] * 65536
        if rom_filename is not None:
            with open(rom_filename, mode="rb") as rom:
                romdata = rom.read()
                for idx, byte in enumerate(romdata):
                    self._mem_array[rom_address + idx] = byte

    def update(self):
        rising_edge = self.clk.is_rising_edge()
        if not rising_edge or self.Address.value == "X":
            return
        addr = self.Address.value
        we = self.WE.value
        if we == 1:
            datain = self.DataIn.value
            self._mem_array[addr] = datain
        else:
            dataout = self._mem_array[addr]
            self.DataOut.value = dataout
