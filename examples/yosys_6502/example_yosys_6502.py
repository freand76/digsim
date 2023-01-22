# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

import os

from digsim.circuit import Circuit
from digsim.circuit.components import Clock, PushButton, YosysComponent
from digsim.circuit.components.atoms import Component, PortIn, PortOut, PortWire


class Memory(Component):
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
        if not self.is_rising_edge(self.clk) or self.Address.value == "X":
            return
        addr = self.Address.value
        we = self.WE.value
        if we == 1:
            datain = self.DataIn.value
            self._mem_array[addr] = datain
        else:
            dataout = self._mem_array[addr]
            self.DataOut.value = dataout


class StringOutput(Component):
    def __init__(self, circuit):
        super().__init__(circuit, "StringOutput")
        self.add_port(PortIn(self, "clk"))
        self.add_port(PortWire(self, "Address", width=16))
        self.add_port(PortWire(self, "DataIn", width=8))
        self.add_port(PortWire(self, "WE"))
        self._str = ""

    def update(self):
        if self.WE.value == 0 or self.Address.value != 0x8000:
            return
        if self.is_rising_edge(self.clk):
            datain = self.DataIn.value
            if datain == 0x0A:
                print(f"OUTPUT: '{self._str}'")
                self._str = ""
            else:
                self._str += chr(datain)


test_circuit = Circuit(vcd="6502.vcd")
rst = PushButton(test_circuit, "RST")
clk = Clock(test_circuit, frequency=1000000, name="CLK")
irq = PushButton(test_circuit, "IRQ")
rdy = PushButton(test_circuit, "RDY")

yosys_6502 = YosysComponent(test_circuit, filename=f"{os.path.dirname(__file__)}/6502.json")
mem = Memory(
    test_circuit, rom_filename=f"{os.path.dirname(__file__)}/code.bin", rom_address=0xF800
)
output = StringOutput(test_circuit)

clk.wire = mem.clk
yosys_6502.AB.wire = mem.Address
yosys_6502.DO.wire = mem.DataIn
yosys_6502.WE.wire = mem.WE
mem.DataOut.wire = yosys_6502.DI

clk.wire = output.clk
yosys_6502.AB.wire = output.Address
yosys_6502.DO.wire = output.DataIn
yosys_6502.WE.wire = output.WE

rst.O.wire = yosys_6502.reset
clk.O.wire = yosys_6502.clk
irq.O.wire = yosys_6502.IRQ
irq.O.wire = yosys_6502.NMI
rdy.O.wire = yosys_6502.RDY

test_circuit.init()
print(yosys_6502)
irq.release()
rdy.push()

rst.push()
test_circuit.run(us=1)
rst.release()
test_circuit.run(us=1)

for _ in range(300):
    test_circuit.run(us=1)
