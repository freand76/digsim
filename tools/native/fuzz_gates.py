# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""
Random circuits of Yosys gate cells, with feedback and with inputs that several cells
drive, run with the engine of DIGSIM_ENGINE. Prints the ports of every cell and writes a
VCD file, both must be the same with DIGSIM_ENGINE=python (see fuzz_engines.sh).

Usage: python tools/native/fuzz_gates.py <seed> <vcd file>
"""

import random
import sys

from digsim.circuit import Circuit
from digsim.circuit.components import GND, VDD
from digsim.circuit.components import _yosys_atoms as atoms
from digsim.circuit.components.atoms import Component, PortOutDelta


class Source(Component):
    def __init__(self, circuit, count):
        super().__init__(circuit, "src")
        for i in range(count):
            self.add_port(PortOutDelta(self, f"o{i}"))


def families():
    """The cell classes by family (their base class), each family as likely"""
    found = {}
    for cls in classes():
        base = cls.__mro__[1]
        found.setdefault(base if base.__name__.startswith("_") else cls, []).append(cls)
    return list(found.values())


def classes():
    found = []
    for name, cls in vars(atoms).items():
        if not (isinstance(cls, type) and issubclass(cls, Component)):
            continue
        if name in ("_FF_", "_StaticLevel_") or not (cls.__doc__ or "").startswith("module"):
            continue
        found.append(cls)
    return found


seed, out = int(sys.argv[1]), sys.argv[2]
rng = random.Random(seed)
circuit = Circuit(vcd=out)
source = Source(circuit, 8)
pool = [source.port(f"o{i}") for i in range(8)]
pool += [GND(circuit).O, VDD(circuit).O]
cells = []
for number in range(rng.randint(20, 60)):
    cls = rng.choice(rng.choice(families()))
    cells.append(cls(circuit, f"c{number}"))
    pool += cells[-1].outports()
for cell in cells:
    for port in cell.inports():
        # Feedback from any output, and sometimes several drivers on one input
        for driver in rng.sample(pool, rng.choice([1, 1, 1, 1, 2, 3])):
            if driver.parent() is cell and rng.random() < 0.7:
                continue
            driver.wire = port
circuit.init()
engine = circuit._engine
if engine is not None:
    native = sum(cell in engine.cells for cell in cells)
    resolved = len(engine._resolved_ports)
    print(f"native cells {native} of {len(cells)}, resolved {resolved}", file=sys.stderr)
for step in range(200):
    for i in rng.sample(range(8), rng.randint(1, 3)):
        source.port(f"o{i}").value = rng.choice([0, 1, 0, 1, "X", "Z"])
    circuit.run(ns=rng.randint(0, 12))
for cell in cells:
    print(cell.name(), [port.value for port in cell.ports])
circuit.vcd_close()
