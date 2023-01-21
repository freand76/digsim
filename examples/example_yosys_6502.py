# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

import os

from digsim.circuit import Circuit
from digsim.circuit.components import Clock, PushButton, YosysComponent


def memory(address):
    mem = {
        0xFFFC: 0x00,
        0xFFFD: 0xC0,
    }
    if address in mem:
        print(f"DI={mem[address]:x}")
        return mem[address]
    return 0x0A


circuit = Circuit(vcd="6502.vcd")
rst = PushButton(circuit, "RST")
clk = Clock(circuit, frequency=1000000, name="CLK")
irq = PushButton(circuit, "IRQ")
rdy = PushButton(circuit, "RDY")

yosys_6502 = YosysComponent(
    circuit, filename=f"{os.path.dirname(__file__)}/../yosys_modules/6502.json"
)

rst.O.wire = yosys_6502.reset
clk.O.wire = yosys_6502.clk
irq.O.wire = yosys_6502.IRQ
irq.O.wire = yosys_6502.NMI
rdy.O.wire = yosys_6502.RDY


circuit.init()
yosys_6502.DI.value = 0
print(yosys_6502)

irq.release()
rdy.push()

rst.push()
circuit.run(us=1)
rst.release()
circuit.run(us=1)

for _ in range(20):
    print(f"AB={yosys_6502.AB.strval()} WE={yosys_6502.WE.strval()}")
    circuit.run(ns=500)
    data = memory(yosys_6502.AB.value)
    yosys_6502.DI.value = data
    circuit.run(ns=500)
