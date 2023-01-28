# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

from digsim.circuit.components.atoms import Component, PortIn, PortOut, PortWire


class Mem64kByte(Component):
    def __init__(self, circuit, rom_filename=None, rom_address=0):
        super().__init__(circuit, "Memory")
        self.add_port(PortIn(self, "clk"))
        self.add_port(PortWire(self, "Address", width=16))
        self.add_port(PortWire(self, "DataIn", width=8))
        self.add_port(PortWire(self, "WE"))
        self.add_port(PortOut(self, "DataOut", width=8))
        self._mem_array = [0] * 65536
        if rom_filename is not None:
            with open(rom_filename, mode="rb") as rom:
                romdata = rom.read()
                for idx, byte in enumerate(romdata):
                    self._mem_array[rom_address + idx] = byte

    def update(self):
        if not self.clk.is_rising_edge() or self.Address.value == "X":
            return
        addr = self.Address.value
        we = self.WE.value
        if we == 1:
            datain = self.DataIn.value
            self._mem_array[addr] = datain
        else:
            dataout = self._mem_array[addr]
            self.DataOut.value = dataout