# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""
Pytest module to test the functional (word-level) Yosys cells: a design synthesized into
functional cells must simulate like the same design synthesized into gates
"""

import json
import random
from pathlib import Path

import pytest

from digsim.circuit import Circuit
from digsim.circuit.components import YosysComponent
from digsim.circuit.components._yosys_functional import (
    DECODER_TYPE,
    FUNCTIONAL_CELLS,
    group_comparisons,
)
from digsim.synth import Synthesis
from digsim.synth._synthesis import _script_files, _script_path
from digsim.utils import YosysCell, YosysNetlist


VERILOG = Path(__file__).parent / "verilog"


def _component(module, functional):
    """A circuit with the module synthesized into gates or into functional cells"""
    circuit = Circuit()
    component = YosysComponent(circuit)
    synthesis = Synthesis([str(VERILOG / f"{module}.v")], module, functional=functional)
    netlist = YosysNetlist(**synthesis.synth_to_dict(silent=True))
    component.create_from_netlist(netlist)
    circuit.init()
    return circuit, component


def _outputs(component):
    return {port.name(): port.value for port in component.outports()}


def test_functional_netlist_has_no_gates():
    """The functional synthesis keeps word-level cells like $add, and has fewer cells"""
    synthesis = Synthesis([str(VERILOG / "functional_comb.v")], "functional_comb", functional=True)
    cells = next(iter(synthesis.synth_to_dict(silent=True)["modules"].values()))["cells"]
    types = {cell["type"] for cell in cells.values()}
    assert "$add" in types
    assert not any(cell_type.startswith("$_") for cell_type in types)
    # Every cell type is simulated
    assert types <= set(FUNCTIONAL_CELLS)


def test_combinational_like_gates():
    """Arithmetic, comparisons, shifts, logic and multiplexers give the same outputs"""
    gate_circuit, gates = _component("functional_comb", functional=False)
    functional_circuit, functional = _component("functional_comb", functional=True)
    rng = random.Random(1)
    for _ in range(300):
        inputs = {
            "a": rng.randrange(16),
            "b": rng.randrange(16),
            "sa": rng.randrange(16),
            "sb": rng.randrange(16),
            "s": rng.randrange(4),
        }
        for circuit, component in ((gate_circuit, gates), (functional_circuit, functional)):
            for name, value in inputs.items():
                component.port(name).value = value
            circuit.run(us=1)
        assert _outputs(functional) == _outputs(gates), inputs


def test_registers_like_gates():
    """Flip-flops with enables and resets, and a latch, give the same outputs"""
    gate_circuit, gates = _component("functional_regs", functional=False)
    functional_circuit, functional = _component("functional_regs", functional=True)
    rng = random.Random(2)
    for _ in range(200):
        inputs = {
            "rst_n": int(rng.random() > 0.1),
            "en": rng.randrange(2),
            "srst": int(rng.random() < 0.2),
            "d": rng.randrange(16),
        }
        for circuit, component in ((gate_circuit, gates), (functional_circuit, functional)):
            for name, value in inputs.items():
                component.port(name).value = value
            circuit.run(us=1)
            component.clk.value = 1
            circuit.run(us=1)
            component.clk.value = 0
            circuit.run(us=1)
        assert _outputs(functional) == _outputs(gates), inputs


def _cell(cell_type, a, b, y, **parameters):
    return YosysCell(
        type=cell_type,
        port_directions={"A": "input", "B": "input", "Y": "output"},
        connections={"A": a, "B": b, "Y": y},
        parameters=parameters,
    )


def test_group_comparisons():
    """Unsigned comparisons of the same nets with constants become one decoder cell"""
    cells = {
        "eq3": _cell("$eq", [2, 3, 4], ["1", "1"], [10]),
        "eq5": _cell("$eq", [2, 3, 4], ["1", "0", "1"], [11]),
        "ne1": _cell("$ne", ["1", "0", "0"], [2, 3, 4], [12]),
        # Other nets, a signed comparison, and two variable operands: kept as they are
        "other": _cell("$eq", [5, 6, 7], ["1", "1", "0"], [13]),
        "signed": _cell("$eq", [2, 3, 4], ["0", "1", "0"], [14], A_SIGNED=1, B_SIGNED=1),
        "variable": _cell("$eq", [2, 3, 4], [5, 6, 7], [15]),
    }
    grouped = group_comparisons(cells)
    assert set(grouped) == {"other", "signed", "variable", "$decoder$0"}
    decoder = grouped["$decoder$0"]
    assert decoder.type == DECODER_TYPE
    assert decoder.connections["A"] == [2, 3, 4]
    assert decoder.connections["Y"] == [10, 11, 12]
    assert [decoder.parameter(f"VALUE{index}") for index in range(3)] == [3, 5, 1]
    assert [decoder.parameter(f"EQUAL{index}") for index in range(3)] == [1, 1, 0]


def test_cell_parameters():
    """Parameters are binary strings in a netlist, undefined bits count as 0"""
    cell = _cell("$adff", [1], [2], [3], WIDTH="00000000000000000000000000000100")
    cell.parameters["ARST_VALUE"] = "1x01"
    assert cell.parameter("WIDTH") == 4
    assert cell.parameter("ARST_VALUE") == 0b1001
    assert cell.parameter("MISSING", 7) == 7
    assert not cell.is_gate
    assert cell.component_type() == "adff"


@pytest.mark.parametrize("functional", [False, True])
def test_undefined_inputs(functional):
    """Before the inputs are set, the outputs that depend on them are undefined"""
    _, component = _component("functional_comb", functional=functional)
    outputs = _outputs(component)
    assert outputs["y_add"] == "X"
    assert outputs["y_case"] == "X"


def test_component_setting():
    """The setting is only stored when it is used, so older versions open the file"""
    circuit = Circuit()
    gates = YosysComponent(circuit, path=VERILOG / "one_module.v")
    functional = YosysComponent(circuit, path=VERILOG / "one_module.v", functional=True)
    assert "functional" not in gates.settings_to_dict()
    assert functional.settings_to_dict()["functional"] is True
    assert "functional" in YosysComponent.get_parameters()


def _alumacc_component():
    """The combinational design synthesized with alumacc: with $alu and $macc_v2 cells"""
    files = _script_files([str(VERILOG / "functional_comb.v")])
    with Synthesis._work_dir() as work_dir:
        json_file = work_dir / "netlist.json"
        script = (
            f"read -sv {files}; hierarchy -top functional_comb; proc; flatten; "
            "synth -noabc -top functional_comb -run begin:fine; memory_map; opt -full; clean; "
            f"write_json {_script_path(json_file)}"
        )
        Synthesis._run_yosys(script, work_dir, [])
        netlist = YosysNetlist(**json.loads(json_file.read_text()))
    types = {cell.type for cell in next(iter(netlist.modules.values())).cells.values()}
    assert {"$alu", "$macc_v2"} <= types
    circuit = Circuit()
    component = YosysComponent(circuit)
    component.create_from_netlist(netlist)
    circuit.init()
    return circuit, component


def test_alumacc_like_gates():
    """A netlist with $alu and $macc_v2 cells (from alumacc) simulates like the gates"""
    gate_circuit, gates = _component("functional_comb", functional=False)
    alu_circuit, alu = _alumacc_component()
    rng = random.Random(3)
    for _ in range(200):
        inputs = {name: rng.randrange(16) for name in ("a", "b", "sa", "sb")}
        inputs["s"] = rng.randrange(4)
        for circuit, component in ((gate_circuit, gates), (alu_circuit, alu)):
            for name, value in inputs.items():
                component.port(name).value = value
            circuit.run(us=1)
        assert _outputs(alu) == _outputs(gates), inputs


def _single_cell(cell_type, ports, **parameters):
    """A component with one cell, and a module port for each port of the cell"""
    net = 2
    module_ports = {}
    connections = {}
    directions = {}
    for name, (direction, width) in ports.items():
        bits = list(range(net, net + width))
        net += width
        module_ports[name] = {"direction": direction, "bits": bits}
        connections[name] = bits
        directions[name] = direction
    cell = {
        "type": cell_type,
        "port_directions": directions,
        "connections": connections,
        "parameters": {name: format(value, "b") for name, value in parameters.items()},
    }
    netlist = YosysNetlist(modules={"single": {"ports": module_ports, "cells": {"cell": cell}}})
    circuit = Circuit()
    component = YosysComponent(circuit)
    component.create_from_netlist(netlist)
    circuit.init()
    return circuit, component


def _run(circuit, component, **inputs):
    for name, value in inputs.items():
        component.port(name).value = value
    circuit.run(ns=10)
    return _outputs(component)


def test_alu_cell():
    """$alu: the sum, the XOR of the operands and the carry out of each bit"""
    circuit, alu = _single_cell(
        "$alu",
        {
            "A": ("input", 4),
            "B": ("input", 4),
            "CI": ("input", 1),
            "BI": ("input", 1),
            "X": ("output", 4),
            "Y": ("output", 4),
            "CO": ("output", 4),
        },
        A_WIDTH=4,
        B_WIDTH=4,
        Y_WIDTH=4,
    )
    for a in range(16):
        for b in range(16):
            for ci, bi in ((0, 0), (1, 1), (1, 0)):
                bb = (~b & 15) if bi else b
                out = _run(circuit, alu, A=a, B=b, CI=ci, BI=bi)
                carries = 0
                carry = ci
                for bit in range(4):
                    x, y = (a >> bit) & 1, (bb >> bit) & 1
                    carry = (x & y) | (x & carry) | (y & carry)
                    carries |= carry << bit
                assert out == {"X": a ^ bb, "Y": (a + bb + ci) & 15, "CO": carries}


def test_macc_v2_cell():
    """$macc_v2: a signed product minus an unsigned addend"""
    circuit, macc = _single_cell(
        "$macc_v2",
        {"A": ("input", 3), "B": ("input", 3), "C": ("input", 4), "Y": ("output", 8)},
        NPRODUCTS=1,
        NADDENDS=1,
        A_WIDTHS=3,
        B_WIDTHS=3,
        C_WIDTHS=4,
        Y_WIDTH=8,
        A_SIGNED=1,
        B_SIGNED=1,
        C_SIGNED=0,
        PRODUCT_NEGATED=0,
        ADDEND_NEGATED=1,
    )

    def signed3(value):
        return value - 8 if value & 4 else value

    for a in range(8):
        for b in range(8):
            for c in (0, 5, 15):
                expected = (signed3(a) * signed3(b) - c) & 0xFF
                assert _run(circuit, macc, A=a, B=b, C=c) == {"Y": expected}


def test_carry_cells():
    """$lcu: carries from propagate and generate, $fa: a full adder for each bit"""
    circuit, lcu = _single_cell(
        "$lcu", {"P": ("input", 4), "G": ("input", 4), "CI": ("input", 1), "CO": ("output", 4)}
    )
    for p in range(16):
        for g in range(16):
            for ci in range(2):
                carry, expected = ci, 0
                for bit in range(4):
                    carry = (g >> bit) & 1 | ((p >> bit) & 1 & carry)
                    expected |= carry << bit
                assert _run(circuit, lcu, P=p, G=g, CI=ci) == {"CO": expected}
    circuit, fa = _single_cell(
        "$fa",
        {
            "A": ("input", 2),
            "B": ("input", 2),
            "C": ("input", 2),
            "X": ("output", 2),
            "Y": ("output", 2),
        },
    )
    for a in range(4):
        for b in range(4):
            for c in range(4):
                assert _run(circuit, fa, A=a, B=b, C=c) == {
                    "X": (a & b) | (c & (a ^ b)),
                    "Y": a ^ b ^ c,
                }


def test_table_cells():
    """$lut: a bit of a table, $sop: a sum of products"""
    circuit, lut = _single_cell("$lut", {"A": ("input", 3), "Y": ("output", 1)}, LUT=0b10010110)
    for a in range(8):
        assert _run(circuit, lut, A=a) == {"Y": (0b10010110 >> a) & 1}
    # Two terms of A[1:0]: A == 0b10 (A[0] 0, A[1] 1), or A[0] == 1 with any A[1]
    table = 0b10_01 | (0b00_10 << 4)
    circuit, sop = _single_cell(
        "$sop", {"A": ("input", 2), "Y": ("output", 1)}, WIDTH=2, DEPTH=2, TABLE=table
    )
    for a in range(4):
        assert _run(circuit, sop, A=a) == {"Y": int(a == 0b10 or a & 1)}


def test_wiring_cells():
    """$concat, $slice, $bweqx and $tribuf"""
    circuit, concat = _single_cell(
        "$concat", {"A": ("input", 3), "B": ("input", 2), "Y": ("output", 5)}
    )
    assert _run(circuit, concat, A=0b101, B=0b11) == {"Y": 0b11101}
    circuit, sliced = _single_cell("$slice", {"A": ("input", 8), "Y": ("output", 3)}, OFFSET=2)
    assert _run(circuit, sliced, A=0b10110100) == {"Y": 0b101}
    circuit, bweqx = _single_cell(
        "$bweqx", {"A": ("input", 4), "B": ("input", 4), "Y": ("output", 4)}
    )
    assert _run(circuit, bweqx, A=0b1100, B=0b1010) == {"Y": 0b1001}
    circuit, tribuf = _single_cell(
        "$tribuf", {"A": ("input", 4), "EN": ("input", 1), "Y": ("output", 4)}
    )
    assert _run(circuit, tribuf, A=0b0110, EN=1) == {"Y": 0b0110}
    # No high impedance value in DigSim: undefined when not enabled
    assert _run(circuit, tribuf, EN=0) == {"Y": "X"}
