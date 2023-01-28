# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

from digsim.circuit.components.atoms import Component, PortIn, PortWire


class MemStdOut(Component):
    def __init__(self, circuit, address=0x8000):
        super().__init__(circuit, "MemStdOut")
        self._address = address
        self.add_port(PortIn(self, "clk"))
        self.add_port(PortWire(self, "Address", width=16))
        self.add_port(PortWire(self, "DataIn", width=8))
        self.add_port(PortWire(self, "WE"))
        self._str = ""

    def update(self):
        if self.WE.value == 0 or self.Address.value != self._address:
            return
        if self.clk.is_rising_edge():
            datain = self.DataIn.value
            if datain == 0x0A:
                print(f"StringOutput [line]: '{self._str}'")
                self._str = ""
            else:
                inchar = chr(datain)
                print(f"StringOutput [char]: '{inchar}'")
                self._str += inchar
