# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""
Pytest module to test the functional (word-level) Yosys cells: a design synthesized into
functional cells must simulate like the same design synthesized into gates
"""

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
