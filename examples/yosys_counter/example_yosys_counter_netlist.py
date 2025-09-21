# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

"""
Example with a component created from a yosys netlist
The yosys netlist is a 4 bit counter created from a verilog file.
The example will generate a gtkwave file, 'counter.vcd'.
"""

import pathlib

from digsim.circuit import Circuit
from digsim.circuit.components import VDD, PushButton, YosysComponent


# Get the path to example folder
example_path = pathlib.Path(__file__).parent

circuit = Circuit()
yosys_counter = YosysComponent(circuit, path=str(example_path / "counter.json"))

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
