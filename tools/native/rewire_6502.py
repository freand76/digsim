# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""
The 6502, with a second driver on RDY for a while during the simulation. Connecting it
stops the native engine, which must hand its state over to Python exactly: the VCD file
must be the same as with DIGSIM_ENGINE=python.

Usage: python tools/native/rewire_6502.py <vcd file>
"""

import sys
from pathlib import Path

from digsim.circuit import Circuit
from digsim.circuit.components import (
    RAM,
    Clock,
    MemStdOut,
    PushButton,
    StaticValue,
    YosysComponent,
)


example = Path(__file__).parents[2] / "examples" / "yosys_6502"
circuit = Circuit(vcd=sys.argv[1])
rst = PushButton(circuit, "RST")
clk = Clock(circuit, frequency=1_000_000, name="CLK")
irq = StaticValue(circuit, "IRQ", value=0)
rdy = StaticValue(circuit, "RDY", value=1)
cpu = YosysComponent(circuit, path=example / "6502_primitives.json", signals=True)
mem = RAM(
    circuit,
    "RAM",
    address_width=16,
    data_width=8,
    mode="sync",
    path=example / "code.bin",
    load_address=0xF800,
)
out = MemStdOut(circuit, address=0x8000)
clk.wire = mem.clk
cpu.AB.wire = mem.Address
cpu.DO.wire = mem.DataIn
cpu.WE.wire = mem.WE
mem.DataOut.wire = cpu.DI
clk.wire = out.clk
cpu.AB.wire = out.Address
cpu.DO.wire = out.DataIn
cpu.WE.wire = out.WE
rst.O.wire = cpu.reset
clk.O.wire = cpu.clk
irq.O.wire = cpu.IRQ
irq.O.wire = cpu.NMI
rdy.O.wire = cpu.RDY
circuit.init()
rst.push()
circuit.run(us=1)
rst.release()
for _ in range(120):
    circuit.run(us=1)
# Stall the CPU with a second driver on RDY, so the port resolves two drivers
low = StaticValue(circuit, "LOW", value=0)
low.O.wire = cpu.RDY
for _ in range(5):
    circuit.run(us=1)
low.O.disconnect(cpu.RDY)
for _ in range(200):
    circuit.run(us=1)
circuit.vcd_close()
