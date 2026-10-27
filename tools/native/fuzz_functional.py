# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""
Random netlists of functional Yosys cells, linked as words, with shared tristate buses,
wide words and "X"/"Z" inputs, run with the engine of DIGSIM_ENGINE. Prints the outputs
and the ports of every cell and writes a VCD file, both must be the same with
DIGSIM_ENGINE=python (see fuzz_engines.sh).

Usage: python tools/native/fuzz_functional.py <seed> <vcd file>
"""

import random
import sys

from digsim.circuit import Circuit
from digsim.circuit.components import YosysComponent
from digsim.utils import YosysNetlist


seed, out = int(sys.argv[1]), sys.argv[2]
rng = random.Random(seed)
net = 2
module_ports = {}
cells = {}
nets = []  # Nets that cells can read
outputs = []  # Output bits of the cells
tribuf_outputs = []


def new_nets(width):
    global net
    bits = list(range(net, net + width))
    net += width
    return bits


def width():
    return rng.choice([1, 1, 2, 3, 4, 5, 8, 12, 16, 33, 64, 70])


def source(count):
    """Bits to read: a word of one net (for links), random nets, or constants"""
    choice = rng.random()
    if choice < 0.4 and outputs:
        word = rng.choice(outputs)
        if len(word) >= count:
            start = rng.randrange(len(word) - count + 1)
            return word[start : start + count]
    if choice < 0.5:
        return [
            rng.choice(["0", "1", "x"]) if rng.random() < 0.3 else rng.choice(nets)
            for _ in range(count)
        ]
    return [rng.choice(nets) for _ in range(count)]


# Module inputs
for index in range(4):
    bits = new_nets(width())
    module_ports[f"in{index}"] = {"direction": "input", "bits": bits}
    nets.extend(bits)
clock = new_nets(1)
module_ports["clk"] = {"direction": "input", "bits": clock}

TYPES = [
    "$alu",
    "$lcu",
    "$fa",
    "$macc_v2",
    "$lut",
    "$sop",
    "$bweqx",
    "$concat",
    "$slice",
    "$tribuf",
    "$add",
    "$mux",
    "$dff",
]
for number in range(rng.randint(5, 25)):
    kind = rng.choice(TYPES)
    w = width()
    params = {}
    ins, outs = {}, {}
    if kind == "$alu":
        aw, bw = width(), width()
        signed = rng.random() < 0.5
        params = {
            "A_SIGNED": signed,
            "B_SIGNED": signed,
            "A_WIDTH": aw,
            "B_WIDTH": bw,
            "Y_WIDTH": w,
        }
        ins = {"A": aw, "B": bw, "CI": 1, "BI": 1}
        outs = {"X": w, "Y": w, "CO": w}
    elif kind == "$lcu":
        params = {"WIDTH": w}
        ins = {"P": w, "G": w, "CI": 1}
        outs = {"CO": w}
    elif kind in ("$fa", "$bweqx"):
        params = {"WIDTH": w}
        ins = {"A": w, "B": w, "C": w} if kind == "$fa" else {"A": w, "B": w}
        outs = {"X": w, "Y": w} if kind == "$fa" else {"Y": w}
    elif kind == "$macc_v2":
        products, addends = rng.randint(0, 3), rng.randint(0, 3)
        a_widths = [rng.randint(1, 8) for _ in range(products)]
        b_widths = [rng.randint(1, 8) for _ in range(products)]
        c_widths = [rng.randint(1, 8) for _ in range(addends)]

        def pack(widths):
            return sum(w << (16 * i) for i, w in enumerate(widths))

        params = {
            "NPRODUCTS": products,
            "NADDENDS": addends,
            "Y_WIDTH": w,
            "A_WIDTHS": pack(a_widths),
            "B_WIDTHS": pack(b_widths),
            "C_WIDTHS": pack(c_widths),
            "A_SIGNED": rng.randrange(1 << max(products, 1)),
            "B_SIGNED": rng.randrange(1 << max(products, 1)),
            "C_SIGNED": rng.randrange(1 << max(addends, 1)),
            "PRODUCT_NEGATED": rng.randrange(1 << max(products, 1)),
            "ADDEND_NEGATED": rng.randrange(1 << max(addends, 1)),
        }
        ins = {"A": max(sum(a_widths), 1), "B": max(sum(b_widths), 1), "C": max(sum(c_widths), 1)}
        outs = {"Y": w}
    elif kind == "$lut":
        w = rng.randint(1, 6)
        params = {"WIDTH": w, "LUT": rng.randrange(1 << (1 << w))}
        ins, outs = {"A": w}, {"Y": 1}
    elif kind == "$sop":
        w, depth = rng.randint(1, 6), rng.randint(1, 4)
        params = {"WIDTH": w, "DEPTH": depth, "TABLE": rng.randrange(1 << (2 * w * depth))}
        ins, outs = {"A": w}, {"Y": 1}
    elif kind == "$concat":
        aw, bw = width(), width()
        params = {"A_WIDTH": aw, "B_WIDTH": bw}
        ins, outs = {"A": aw, "B": bw}, {"Y": aw + bw}
    elif kind == "$slice":
        aw = width()
        offset = rng.randrange(aw)
        params = {"A_WIDTH": aw, "Y_WIDTH": rng.randint(1, aw - offset), "OFFSET": offset}
        ins, outs = {"A": aw}, {"Y": params["Y_WIDTH"]}
    elif kind == "$tribuf":
        params = {"WIDTH": w}
        ins, outs = {"A": w, "EN": 1}, {"Y": w}
    elif kind == "$add":
        params = {"A_SIGNED": 0, "B_SIGNED": 0, "A_WIDTH": w, "B_WIDTH": w, "Y_WIDTH": w}
        ins, outs = {"A": w, "B": w}, {"Y": w}
    elif kind == "$mux":
        params = {"WIDTH": w}
        ins, outs = {"A": w, "B": w, "S": 1}, {"Y": w}
    else:
        params = {"WIDTH": w, "CLK_POLARITY": 1}
        ins, outs = {"CLK": 1, "D": w}, {"Q": w}
    connections, directions = {}, {}
    for name, count in ins.items():
        connections[name] = clock if name == "CLK" else source(count)
        directions[name] = "input"
    for name, count in outs.items():
        if kind == "$tribuf" and tribuf_outputs and rng.random() < 0.5:
            # Drive the nets of another tristate buffer: a shared bus
            other = rng.choice(tribuf_outputs)
            if len(other) == count:
                connections[name] = other
                directions[name] = "output"
                continue
        bits = new_nets(count)
        connections[name] = bits
        directions[name] = "output"
        outputs.append(bits)
        if kind == "$tribuf":
            tribuf_outputs.append(bits)
    nets.extend(bit for name in outs for bit in connections[name])
    cells[f"c{number}"] = {
        "type": kind,
        "port_directions": directions,
        "connections": connections,
        "parameters": {name: format(int(value), "b") for name, value in params.items()},
    }
for index, bits in enumerate(rng.sample(outputs, min(len(outputs), 6))):
    module_ports[f"out{index}"] = {"direction": "output", "bits": bits}

netlist = YosysNetlist(modules={"fuzz": {"ports": module_ports, "cells": cells}})
circuit = Circuit(vcd=out)
component = YosysComponent(circuit)
component.create_from_netlist(netlist)
circuit.init()
engine = circuit._engine
if engine is not None:
    from digsim.circuit.components._yosys_functional import FunctionalCell

    functional_cells = [c for c in circuit._components.values() if isinstance(c, FunctionalCell)]
    print(f"native cells {len(engine.word_cells)} of {len(functional_cells)}", file=sys.stderr)
for step in range(150):
    for index in rng.sample(range(4), rng.randint(1, 2)):
        port = component.port(f"in{index}")
        port.value = rng.choice(["X", "Z", rng.randrange(1 << port.width), rng.randrange(4)])
    component.port("clk").value = step & 1
    circuit.run(ns=rng.randint(0, 20))
    print(step, [port.value for port in component.outports()])
for comp in circuit._components.values():
    print(comp.name(), [port.value for port in comp.ports])
circuit.vcd_close()
