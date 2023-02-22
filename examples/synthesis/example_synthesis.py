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
from digsim.circuit.components import Clock, PushButton, YosysComponent
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

# Create components in circuit, Clock, Reset button and Yosys component (fibonacci)

clk = Clock(circuit, "clk", frequency=1000)
reset = PushButton(circuit, "reset")
synth_component = YosysComponent(circuit, path=yosys_output_file)

# Connect clock and reset button to synth_component (fibonacci)

clk.O.wire = synth_component.clk
reset.O.wire = synth_component.reset

# Initialize circuit
circuit.init()

# Push reset button and run the simulation for 1ms
reset.push()
circuit.run(ms=1)

print("\n===================== Reset ==========================\n")

# Print component info
print(synth_component)

print("\n===================== Start ==========================\n")

# Release reset button and run the simulation for 1us
reset.release()
circuit.run(us=1)

# Run simulation in 16ms (in steps of 1ms, print the index and value each loop)
for _ in range(0, 16):
    index = synth_component.index.value
    value = synth_component.value.value
    print(f"Fibonacci sequence [{index}] value is {value}")
    circuit.run(ms=1)
