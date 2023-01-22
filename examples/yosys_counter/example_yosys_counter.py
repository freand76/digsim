# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

import os

from digsim.circuit import Circuit
from digsim.circuit.components import VDD, PushButton, YosysComponent


circuit = Circuit()
yosys_counter = YosysComponent(circuit, filename=f"{os.path.dirname(__file__)}/counter.json")

clk = PushButton(circuit, "clk")
reset = PushButton(circuit, "reset")

vdd = VDD(circuit)
clk.O.wire = yosys_counter.clk
reset.O.wire = yosys_counter.reset
vdd.wire = yosys_counter.up
circuit.init()


circuit.run(ms=10)
reset.push()
circuit.run(ms=10)
reset.release()
circuit.run(ms=10)

circuit.vcd("counter.vcd")

print("\n===================== Reset ==========================\n")

print(yosys_counter)

print("\n===================== Start ==========================\n")

for _ in range(0, 16):
    print("OUT", yosys_counter.cnt.value)

    clk.push()
    circuit.run(ms=10)
    clk.release()
    circuit.run(ms=10)
