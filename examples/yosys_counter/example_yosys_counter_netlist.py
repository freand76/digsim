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


# Get the relative path to example folder
example_path = pathlib.Path(__file__).parent.relative_to(pathlib.Path.cwd())

# Create a new circuit
circuit = Circuit()

# Instantiate the Yosys counter component from its netlist
yosys_counter = YosysComponent(circuit, path=str(example_path / "counter.json"))

# Instantiate clock and reset push buttons
clk = PushButton(circuit, "clk")
reset = PushButton(circuit, "reset")

# Instantiate a VDD (logic high) component
vdd = VDD(circuit)

# --- Wire up the components ---
# Connect clock and reset buttons to the counter
clk.O.wire = yosys_counter.clk
reset.O.wire = yosys_counter.reset
# Connect VDD to the 'up' input of the counter (assuming it's an up/down counter)
vdd.wire = yosys_counter.up

# Initialize the circuit
circuit.init()


# --- Simulation sequence ---
# Run for a short period
circuit.run(ms=10)

# Apply and release reset
reset.push()
circuit.run(ms=10)
reset.release()
circuit.run(ms=10)

# Start VCD recording
circuit.vcd("counter.vcd")

print("\n===================== Reset ==========================\n")

print(yosys_counter)

print("\n===================== Start ==========================\n")

# Simulate 16 clock cycles and print the counter value
for _ in range(0, 16):
    print("OUT", yosys_counter.cnt.value)

    clk.push()
    circuit.run(ms=10)
    clk.release()
    circuit.run(ms=10)
