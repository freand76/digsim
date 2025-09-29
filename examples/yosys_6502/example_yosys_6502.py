# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""
Example with a component created from a yosys netlist
The yosys netlist is a 6502 CPU created from a verilog file.
The 6502 is connected to two memory mapped components,
one 64kByte memory and one memory mapped 'stdout' writer.
The example code that is loaded into the memory before the
simulation starts will send the characters 'Hello World' to
the MemStdOut component.
The example will generate a gtkwave file, '6502.vcd'.
"""

import pathlib

from digsim.circuit import Circuit
from digsim.circuit.components import (
    Clock,
    Mem64kByte,
    MemStdOut,
    PushButton,
    StaticValue,
    YosysComponent,
)


# Get the relative path to the example folder
example_path = pathlib.Path(__file__).parent.resolve().relative_to(pathlib.Path.cwd())

# Create a new circuit with VCD output
test_circuit = Circuit(vcd="6502.vcd")

# Instantiate components
rst = PushButton(test_circuit, "RST")
clk = Clock(test_circuit, frequency=1000000, name="CLK")
irq = StaticValue(test_circuit, "IRQ", value=0)
rdy = StaticValue(test_circuit, "RDY", value=1)

# Instantiate the 6502 Yosys component, memory, and stdout output
yosys_6502 = YosysComponent(test_circuit, path=example_path / "6502.json")
mem = Mem64kByte(test_circuit, rom_filename=example_path / "code.bin", rom_address=0xF800)
output = MemStdOut(test_circuit, address=0x8000)

# --- Wire up the components ---
# Clock and memory
clk.wire = mem.clk
yosys_6502.AB.wire = mem.Address
yosys_6502.DO.wire = mem.DataIn
yosys_6502.WE.wire = mem.WE
mem.DataOut.wire = yosys_6502.DI

# Clock and stdout output
clk.wire = output.clk
yosys_6502.AB.wire = output.Address
yosys_6502.DO.wire = output.DataIn
yosys_6502.WE.wire = output.WE

# Control signals for 6502
rst.O.wire = yosys_6502.reset
clk.O.wire = yosys_6502.clk
irq.O.wire = yosys_6502.IRQ
irq.O.wire = yosys_6502.NMI
rdy.O.wire = yosys_6502.RDY

# Initialize the circuit
test_circuit.init()
print(yosys_6502)

# --- Simulation sequence ---
# Apply and release reset
rst.push()
test_circuit.run(us=1)
rst.release()
test_circuit.run(us=1)

# Run simulation for a number of clock cycles
for _ in range(300):
    test_circuit.run(us=1)
