# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

"""
Example with synthesis of a verilog file, then creation of a yosys
component from the synthesized netlist.
The verilog file describes a fibonacci sequence generator
The example will generate a gtkwave file, 'fibonacci.vcd'.
"""

import os
import sys

from digsim.circuit import Circuit
from digsim.circuit.components import YosysComponent
from digsim.synth import Synthesis


# Do verilog synthesis with Yosys (with helper python class)
# Input file fibonacci.v will generate fibonacci.json

input_verilog_file = f"{os.path.dirname(__file__)}/fibonacci.v"
yosys_output_file = f"{os.path.dirname(__file__)}/fibonacci.json"

print(f"Start synthesis of '{input_verilog_file}'")
synthesis = Synthesis(input_verilog_file, yosys_output_file, "fibonacci")
if not synthesis.execute(silent=True):
    # print log and exit if error occurs
    print("\n======== Yosys Log ========")
    log = synthesis.get_log()
    for line in log:
        print(f"YOSYS {line}")
    print("======== Yosys Log ========\n")
    sys.exit(1)
print("Synthesis done!")

# Create circuit for simulation

circuit = Circuit(vcd="fibonacci.vcd")

# Create Yosys component (fibonacci) component in circuit

synth_component = YosysComponent(circuit, path=yosys_output_file)
synth_component1 = YosysComponent(circuit, path=yosys_output_file)
synth_component2 = YosysComponent(circuit, path=yosys_output_file)


# Initialize circuit
circuit.init()

# Run for 1 ms
circuit.run(ms=1)

# Set reset signal high for 1ms
synth_component.reset.value = 1
circuit.run(ms=1)

print("\n===================== Reset ==========================\n")

# Print component info
print(synth_component)

print("\n===================== Start ==========================\n")

# Set reset signal low for 1ms
synth_component.reset.value = 0
circuit.run(ms=1)

# Loop 16 times (print the index and value + generate clock cycle)
for _ in range(0, 16):
    index = synth_component.index.value
    value = synth_component.value.value
    print(f"Fibonacci sequence [{index}] value is {value}")

    # Set clock signal high for 1ms
    synth_component.clk.value = 1
    circuit.run(ms=1)
    # Set clock signal low for 1ms
    synth_component.clk.value = 0
    circuit.run(ms=1)
