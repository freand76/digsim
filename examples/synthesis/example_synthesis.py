# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

"""
Example with synthesis of a verilog file, then creation of a yosys
component from the synthesized netlist.
The verilog file describes a fibonacci sequence generator
The example will generate a gtkwave file, 'fibonacci.vcd'.
"""

import pathlib
import sys

from digsim.circuit import Circuit
from digsim.circuit.components import YosysComponent
from digsim.synth import Synthesis, SynthesisException


# Get the relative path to example folder
example_path = pathlib.Path(__file__).parent.resolve().relative_to(pathlib.Path.cwd())

# Do verilog synthesis with Yosys (with helper python class)
# Input file fibonacci.v will generate fibonacci.json

input_verilog_path = example_path / "fibonacci.v"
yosys_json_output_path = example_path / "fibonacci.json"

print(f"Start synthesis of '{input_verilog_path}'")
synthesis = Synthesis(input_verilog_path, "fibonacci")
try:
    synthesis.synth_to_json_file(yosys_json_output_path, silent=True)
except SynthesisException:
    # print log and exit if error occurs
    print("\n======== Yosys Log ========")
    log = synthesis.get_log()
    for line in log:
        print(f"YOSYS {line}")
    print("======== Yosys Log ========\n")
    print("Synthesis with error!")
    sys.exit(1)
print("Synthesis done!")

# Create circuit for simulation

circuit = Circuit(vcd="fibonacci.vcd")

# Create Yosys component (fibonacci) component in circuit

synth_component = YosysComponent(circuit, path=yosys_json_output_path)

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
