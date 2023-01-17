# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

import os

from digsim.circuit import Circuit
from digsim.circuit.components import PushButton, YosysComponent


circuit = Circuit(vcd="6502.vcd")
rst = PushButton(circuit, "RST")
clk = PushButton(circuit, "CLK")

yosys_6502 = YosysComponent(
    circuit, filename=f"{os.path.dirname(__file__)}/../yosys_modules/6502.json"
)

rst.O.wire = yosys_6502.RST
clk.O.wire = yosys_6502.clk

circuit.init()

rst.push()
circuit.run(ms=10)

circuit.run(ms=10)
clk.push()
circuit.run(ms=10)
clk.release()

rst.release()

yosys_6502.DI.set_level(value=0x80)

for _ in range(10):
    print(yosys_6502)
    circuit.run(ms=10)
    clk.push()
    print(yosys_6502)
    circuit.run(ms=10)
    clk.release()
