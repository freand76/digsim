# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

import os

from digsim.circuit import Circuit
from digsim.circuit.components import PushButton, YosysComponent


def memory(address):
    mem = {
        0xFFFC: 0x00,
        0xFFFD: 0xC0,
    }
    if address in mem:
        print(f"DI={mem[address]:x}")
        return mem[address]
    return 0


circuit = Circuit(vcd="6502.vcd")
rst = PushButton(circuit, "RST")
clk = PushButton(circuit, "CLK")

yosys_6502 = YosysComponent(
    circuit, filename=f"{os.path.dirname(__file__)}/../yosys_modules/6502.json"
)

rst.O.wire = yosys_6502.RST
clk.O.wire = yosys_6502.clk

circuit.init()

clk.release()
rst.push()
circuit.run(ns=500)
clk.push()
circuit.run(ns=500)
clk.release()
rst.release()


for _ in range(10):
    data = memory(int(yosys_6502.AB.bitval, 16))
    circuit.run(ns=500)
    print(f"AB={yosys_6502.AB.bitval} WE={yosys_6502.WE.bitval}")
    circuit.run(ns=500)
    clk.push()
    circuit.run(ns=500)
    yosys_6502.DI.set_level(value=data)
    clk.release()
