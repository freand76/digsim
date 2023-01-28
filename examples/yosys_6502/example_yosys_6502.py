# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

import os

from digsim.circuit import Circuit
from digsim.circuit.components import Clock, Mem64kByte, MemStdOut, PushButton, YosysComponent


test_circuit = Circuit(vcd="6502.vcd")
rst = PushButton(test_circuit, "RST")
clk = Clock(test_circuit, frequency=1000000, name="CLK")
irq = PushButton(test_circuit, "IRQ")
rdy = PushButton(test_circuit, "RDY")

yosys_6502 = YosysComponent(test_circuit, filename=f"{os.path.dirname(__file__)}/6502.json")
mem = Mem64kByte(
    test_circuit, rom_filename=f"{os.path.dirname(__file__)}/code.bin", rom_address=0xF800
)
output = MemStdOut(test_circuit, address=0x8000)

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