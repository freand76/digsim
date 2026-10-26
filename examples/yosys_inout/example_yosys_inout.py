# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""
Example with Verilog inout ports: two registers (bus_register.v) on a shared 8-bit data
bus, and a tristate buffer that drives the bus like a CPU. A value is written to the
first register, copied over the bus to the second, and read back. The example writes a
gtkwave file, 'bus_register.vcd'.
"""

import pathlib

from digsim.circuit import Circuit
from digsim.circuit.components import TristateBuffer, YosysComponent


# Get the relative path to example folder
example_path = pathlib.Path(__file__).parent.relative_to(pathlib.Path.cwd())

circuit = Circuit(vcd="bus_register.vcd")

# Two registers from the same Verilog file, the second is named bus_register_1
reg_a = YosysComponent(circuit, path=str(example_path / "bus_register.v"))
reg_b = YosysComponent(circuit, path=str(example_path / "bus_register.v"))

# The CPU drives the bus through a tristate buffer, only while its OE is high
cpu = TristateBuffer(circuit, "cpu", width=8)

# --- Wire up the bus ---
# Every port on the bus drives the others: the inout ports drive each other both ways
cpu.Y.wire = reg_a.data
cpu.Y.wire = reg_b.data
reg_a.data.wire = reg_b.data
reg_b.data.wire = reg_a.data

circuit.init()

# The control inputs are set directly, like in a testbench
for port in (reg_a.clk, reg_a.we, reg_a.oe, reg_b.clk, reg_b.we, reg_b.oe, cpu.OE):
    port.value = 0
circuit.run(ns=10)


def clock():
    """A clock cycle for both registers"""
    reg_a.clk.value = 1
    reg_b.clk.value = 1
    circuit.run(ns=10)
    reg_a.clk.value = 0
    reg_b.clk.value = 0
    circuit.run(ns=10)


def hex_value(value):
    """A value in hex, or "X" (undefined) or "Z" (not driven)"""
    return value if isinstance(value, str) else f"0x{value:02x}"


def show(step):
    """
    The value of the bus, as the first register reads it, what the first register drives
    on it, and the values of the registers
    """
    print(
        f"{step:<34} bus={hex_value(reg_a.data.read_value()):<5}"
        f"a drives={hex_value(reg_a.data.value):<5}"
        f"a={hex_value(reg_a.value.value):<5}b={hex_value(reg_b.value.value)}"
    )


show("Start, nothing drives the bus")

# The CPU writes 0x5a to the first register
cpu.A.value = 0x5A
cpu.OE.value = 1
reg_a.we.value = 1
circuit.run(ns=10)
show("CPU drives 0x5a")
clock()
show("Register a stores it")
cpu.OE.value = 0
reg_a.we.value = 0
circuit.run(ns=10)

# The first register drives the bus, the second stores the value
reg_a.oe.value = 1
reg_b.we.value = 1
circuit.run(ns=10)
show("Register a drives the bus")
clock()
show("Register b stores it")
reg_a.oe.value = 0
reg_b.we.value = 0
circuit.run(ns=10)

# The CPU reads the second register
reg_b.oe.value = 1
circuit.run(ns=10)
show("Register b drives the bus")

# Two drivers with different values: the bus is undefined
cpu.A.value = 0x33
cpu.OE.value = 1
circuit.run(ns=10)
show("CPU drives 0x33 too (contention)")
reg_b.oe.value = 0
cpu.OE.value = 0
circuit.run(ns=10)
show("Nothing drives the bus")

circuit.vcd_close()
