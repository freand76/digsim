# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""
Random Yosys netlists without combinational loops, of gate cells or of functional
cells (with flip-flops, latches, "X" inputs and comparisons that become a decoder), run
with the engine of DIGSIM_ENGINE. The native engine simulates them as compiled blocks
(zero delay inside), the Python engine with a delay for each cell, so the inputs change,
the circuit settles and then the clock changes, and the outputs are printed when the
circuit has settled: they must be the same with DIGSIM_ENGINE=python (see
fuzz_blocks.sh). The asynchronous controls (resets, latch enables) are module inputs: a
glitch on one (which differs with and without delays) would change the state.

Usage: python tools/native/fuzz_blocks.py <gates|functional> <seed>
"""

import random
import sys

from digsim.circuit import Circuit
from digsim.circuit.components import YosysComponent
from digsim.utils import YosysNetlist


mode, seed = sys.argv[1], int(sys.argv[2])
rng = random.Random(seed)
net = 2
module_ports = {}
cells = {}
nets = []  # Nets that cells can read
outputs = []  # Output words of the cells


def new_nets(width):
    global net
    bits = list(range(net, net + width))
    net += width
    return bits


def width():
    return rng.choice([1, 1, 2, 3, 4, 5, 7, 8, 12, 16, 31, 32, 33, 64, 70])


def source(count):
    """Bits to read: a word of an output, random nets, or constants"""
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


def add_cell(kind, params, ins, outs, fixed=None):
    connections, directions = {}, {}
    for name, count in ins.items():
        connections[name] = (fixed or {}).get(name) or source(count)
        directions[name] = "input"
    for name, count in outs.items():
        bits = new_nets(count)
        connections[name] = bits
        directions[name] = "output"
        outputs.append(bits)
    new = [bit for name in outs for bit in connections[name]]
    cells[f"c{len(cells)}"] = {
        "type": kind,
        "port_directions": directions,
        "connections": connections,
        "parameters": {name: format(int(value), "b") for name, value in params.items()},
    }
    return new


# Module inputs, and a clock
inputs = []  # Their bits: the asynchronous controls (resets, latch enables) read them only
for index in range(4):
    bits = new_nets(width() if mode == "functional" else rng.randint(1, 8))
    module_ports[f"in{index}"] = {"direction": "input", "bits": bits}
    nets.extend(bits)
    inputs.extend(bits)
clock = new_nets(1)
module_ports["clk"] = {"direction": "input", "bits": clock}

UNARY = ["$not", "$pos", "$neg", "$reduce_and", "$reduce_or", "$reduce_xor"]
UNARY += ["$reduce_xnor", "$reduce_bool", "$logic_not"]
BINARY = ["$and", "$or", "$xor", "$xnor", "$add", "$sub", "$mul", "$lt", "$le", "$gt"]
BINARY += ["$ge", "$eq", "$ne", "$eqx", "$nex", "$logic_and", "$logic_or", "$shl", "$shr"]
BINARY += ["$sshl", "$sshr", "$shift", "$shiftx"]
REGISTERS = ["$dff", "$dffe", "$sdff", "$sdffe", "$sdffce", "$adff", "$adffe", "$dlatch"]
GATES = {
    "$_BUF_": "A",
    "$_NOT_": "A",
    "$_AND_": "AB",
    "$_NAND_": "AB",
    "$_OR_": "AB",
    "$_NOR_": "AB",
    "$_XOR_": "AB",
    "$_XNOR_": "AB",
    "$_ANDNOT_": "AB",
    "$_ORNOT_": "AB",
    "$_MUX_": "ABS",
    "$_NMUX_": "ABS",
    "$_AOI3_": "ABC",
    "$_OAI3_": "ABC",
    "$_AOI4_": "ABCD",
    "$_OAI4_": "ABCD",
    "$_MUX4_": "ABCDST",
}
FLOPS = {
    "$_DFF_P_": "D",
    "$_DFF_N_": "D",
    "$_DFFE_PP_": "DE",
    "$_DFFE_PN_": "DE",
    "$_SDFF_PP0_": "DR",
    "$_SDFF_PN1_": "DR",
    "$_SDFFE_PP0P_": "DRE",
    "$_SDFFCE_PP1P_": "DRE",
    "$_DFF_PP0_": "DR",
    "$_DFF_PN1_": "DR",
    "$_DFFSR_PPP_": "DSR",
    "$_DLATCH_P_": "D",
}

for _ in range(rng.randint(10, 60)):
    if mode == "gates":
        if rng.random() < 0.2:
            kind = rng.choice(list(FLOPS))
            ins = {name: 1 for name in FLOPS[kind]}
            control = "E" if kind.startswith("$_DLATCH") else "C"
            ins[control] = 1
            fixed = {"E": [rng.choice(inputs)]} if control == "E" else {"C": clock}
            # A glitch of a combinational cell would set or reset these at once: with
            # a delay for each cell the glitches differ, without none
            if kind.startswith(("$_DFF_P", "$_DFFSR")):
                fixed.update({name: [rng.choice(inputs)] for name in "RS" if name in ins})
            new = add_cell(kind, {}, ins, {"Q": 1}, fixed)
        else:
            kind = rng.choice(list(GATES))
            new = add_cell(kind, {}, {name: 1 for name in GATES[kind]}, {"Y": 1})
        nets.extend(new)
        continue
    w = width()
    choice = rng.random()
    if choice < 0.2:
        kind = rng.choice(UNARY)
        aw = width()
        params = {"A_SIGNED": rng.random() < 0.3, "A_WIDTH": aw, "Y_WIDTH": w}
        new = add_cell(kind, params, {"A": aw}, {"Y": w})
    elif choice < 0.55:
        kind = rng.choice(BINARY)
        aw, bw = width(), rng.choice([width(), rng.randint(1, 7)])
        signed = rng.random() < 0.3
        params = {"A_SIGNED": signed, "B_SIGNED": signed, "A_WIDTH": aw, "B_WIDTH": bw}
        params["Y_WIDTH"] = w
        new = add_cell(kind, params, {"A": aw, "B": bw}, {"Y": w})
    elif choice < 0.62:
        # Comparisons of the same word with constants: one decoder
        aw = rng.randint(1, 8)
        word = source(aw)
        new = []
        for _ in range(rng.randint(2, 6)):
            constant = [rng.choice("01") for _ in range(aw)]
            kind = rng.choice(["$eq", "$ne"])
            params = {"A_SIGNED": 0, "B_SIGNED": 0, "A_WIDTH": aw, "B_WIDTH": aw, "Y_WIDTH": 1}
            fixed = {"A": word, "B": constant}
            new += add_cell(kind, params, {"A": aw, "B": aw}, {"Y": 1}, fixed)
    elif choice < 0.72:
        kind = rng.choice(["$mux", "$pmux", "$bmux", "$bwmux", "$demux"])
        s = rng.randint(1, 4)
        if kind == "$mux":
            params, ins, outs = {"WIDTH": w}, {"A": w, "B": w, "S": 1}, {"Y": w}
        elif kind == "$pmux":
            params = {"WIDTH": w, "S_WIDTH": s}
            ins, outs = {"A": w, "B": w * s, "S": s}, {"Y": w}
        elif kind == "$bmux":
            w = rng.randint(1, 16)
            params, ins, outs = {"WIDTH": w, "S_WIDTH": s}, {"A": w << s, "S": s}, {"Y": w}
        elif kind == "$bwmux":
            params, ins, outs = {"WIDTH": w}, {"A": w, "B": w, "S": w}, {"Y": w}
        else:
            w = rng.randint(1, 8)
            params, ins, outs = {"WIDTH": w, "S_WIDTH": s}, {"A": w, "S": s}, {"Y": w << s}
        new = add_cell(kind, params, ins, outs)
    elif choice < 0.8:
        kind = rng.choice(["$concat", "$slice"])
        if kind == "$concat":
            aw, bw = width(), width()
            params, ins, outs = {"A_WIDTH": aw, "B_WIDTH": bw}, {"A": aw, "B": bw}, {"Y": aw + bw}
        else:
            aw = width()
            offset = rng.randrange(aw)
            yw = rng.randint(1, aw - offset)
            params = {"A_WIDTH": aw, "Y_WIDTH": yw, "OFFSET": offset}
            ins, outs = {"A": aw}, {"Y": yw}
        new = add_cell(kind, params, ins, outs)
    else:
        kind = rng.choice(REGISTERS)
        params = {"WIDTH": w, "CLK_POLARITY": rng.random() < 0.8, "EN_POLARITY": 1}
        ins = {"CLK": 1, "D": w}
        if kind in ("$dffe", "$sdffe", "$sdffce", "$adffe"):
            ins["EN"] = 1
        if kind.startswith("$sdff"):
            ins["SRST"] = 1
            params["SRST_POLARITY"] = rng.random() < 0.5
            params["SRST_VALUE"] = rng.randrange(1 << w)
        if kind.startswith("$adff"):
            ins["ARST"] = 1
            params["ARST_POLARITY"] = rng.random() < 0.5
            params["ARST_VALUE"] = rng.randrange(1 << w)
        fixed = {"CLK": clock}
        if kind.startswith("$adff"):
            fixed["ARST"] = [rng.choice(inputs)]
        if kind == "$dlatch":
            ins = {"EN": 1, "D": w}
            fixed = {"EN": [rng.choice(inputs)]}
        new = add_cell(kind, params, ins, {"Q": w}, fixed)
    nets.extend(new)
for index, bits in enumerate(outputs):
    module_ports[f"out{index}"] = {"direction": "output", "bits": bits}

netlist = YosysNetlist(modules={"fuzz": {"ports": module_ports, "cells": cells}})
circuit = Circuit()
component = YosysComponent(circuit)
component.create_from_netlist(netlist)
circuit.init()
circuit.run(ns=1000)
for step in range(60):
    for index in rng.sample(range(4), rng.randint(1, 2)):
        port = component.port(f"in{index}")
        port.value = rng.choice(["X", rng.randrange(1 << port.width), rng.randrange(4), 0])
    circuit.run(ns=1000)
    component.port("clk").value = step & 1
    circuit.run(ns=1000)
    print(step, [port.value for port in component.outports()])
