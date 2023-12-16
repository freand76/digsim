# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

"""
Example with a component created from a verilog file (counter.v)
The example will generate a gtkwave file, 'counter.vcd'.
"""

import os

from digsim.circuit import Circuit
from digsim.circuit.components import VDD, PushButton, YosysComponent


# Get the relative path to example folder
example_path = os.path.relpath(os.path.dirname(os.path.abspath(__file__)), os.getcwd())

circuit = Circuit()
yosys_counter = YosysComponent(circuit, path=f"{example_path}/counter.v")

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
