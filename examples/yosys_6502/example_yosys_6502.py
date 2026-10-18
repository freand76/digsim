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

The CPU is synthesized into gates (6502_primitives.json), or with
'--functional' into functional blocks like adders and multiplexers
(6502_functional.json), which simulates faster. See verilog/synth.sh.
After the simulation, the example prints how many clock cycles it
simulated per second.

Waveforms are not written by default, since that makes the simulation
slower. Use '--vcd' to write them to '6502.vcd', or '--vcd <file>' to
choose the file name.

With '--signals', the internal signals of the CPU, like the program
counter and the registers, are readable and written to the VCD file, and
the example prints the registers after the simulation. The state of the
CPU is written with the names of its states (the parameters in cpu.v).
"""

import argparse
import pathlib
import time

from digsim.circuit import Circuit
from digsim.circuit.components import (
    Clock,
    Mem64kByte,
    MemStdOut,
    PushButton,
    StaticValue,
    YosysComponent,
)


CLOCK_HZ = 1_000_000

# Get the relative path to the example folder
example_path = pathlib.Path(__file__).parent.resolve().relative_to(pathlib.Path.cwd())

parser = argparse.ArgumentParser(description="Simulate a 6502 CPU printing 'Hello World'")
parser.add_argument(
    "--vcd",
    nargs="?",
    const="6502.vcd",
    default=None,
    metavar="FILE",
    help="write waveforms to a VCD file (default file: 6502.vcd)",
)
parser.add_argument(
    "--functional",
    action="store_true",
    help="use the CPU synthesized into functional blocks (6502_functional.json)",
)
parser.add_argument(
    "--signals",
    action="store_true",
    help="make the internal signals of the CPU readable and write them to the VCD file",
)
args = parser.parse_args()
netlist = "6502_functional.json" if args.functional else "6502_primitives.json"

# Create a new circuit, with VCD output if requested
test_circuit = Circuit(vcd=args.vcd)

# Instantiate components
rst = PushButton(test_circuit, "RST")
clk = Clock(test_circuit, frequency=CLOCK_HZ, name="CLK")
irq = StaticValue(test_circuit, "IRQ", value=0)
rdy = StaticValue(test_circuit, "RDY", value=1)

# Instantiate the 6502 Yosys component, memory, and stdout output
yosys_6502 = YosysComponent(
    test_circuit,
    path=example_path / netlist,
    signals=args.signals,
    states=["state"] if args.signals else None,
)
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
# Only the simulation is timed, not loading the netlist
start_time = time.perf_counter()
start_ns = test_circuit.time_ns

# Apply and release reset
rst.push()
test_circuit.run(us=1)
rst.release()
test_circuit.run(us=1)

# Run simulation for a number of clock cycles
for _ in range(300):
    test_circuit.run(us=1)

elapsed = time.perf_counter() - start_time
clock_cycles = (test_circuit.time_ns - start_ns) * CLOCK_HZ // 1_000_000_000
print(
    f"Simulated {clock_cycles} clock cycles of {netlist} in {elapsed:.2f} s: "
    f"{clock_cycles / elapsed:.0f} clocks/second"
)

if args.signals:
    # A few of the internal signals: the registers (AXYS holds A, S, X and Y), the
    # program counter, the status register and the state of the CPU
    a, s, x, y = (yosys_6502.signal(f"AXYS[{index}]") for index in range(4))
    print(
        f"CPU: PC={yosys_6502.signal('PC'):04X} A={a:02X} X={x:02X} Y={y:02X} S={s:02X} "
        f"P={yosys_6502.signal('P'):02X} state={yosys_6502.state('state')}"
    )
