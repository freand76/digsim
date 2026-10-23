# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""A reload that can't be built leaves the Yosys component as it was"""

import copy
from pathlib import Path

import pytest

from digsim.circuit import Circuit
from digsim.circuit.components import PushButton, YosysComponent
from digsim.circuit.components._yosys_component import YosysComponentException
from digsim.utils import YosysNetlist


COUNTER = Path(__file__).parent.parent / "examples" / "yosys_counter" / "counter.v"
FSM_PARAMETERS = Path(__file__).parent / "verilog" / "fsm_parameters.v"


def _counter(**settings):
    circuit = Circuit()
    counter = YosysComponent(circuit, path=COUNTER, **settings)
    buttons = {name: PushButton(circuit, name) for name in ("clk", "reset", "up")}
    for name, button in buttons.items():
        button.O.wire = counter.port(name)
    circuit.init()
    return circuit, counter, buttons


def _counts(circuit, counter, buttons, clocks):
    """The counter still counts: it was not taken apart"""
    circuit.init()
    buttons["reset"].push()
    circuit.run(ms=1)
    buttons["reset"].release()
    buttons["up"].push()
    for _ in range(clocks):
        buttons["clk"].push()
        circuit.run(ms=1)
        buttons["clk"].release()
        circuit.run(ms=1)
    return counter.cnt.value == clocks


def _netlist(change=None):
    netlist_dict = copy.deepcopy(YosysComponent.synthesize_file(COUNTER))
    if change is not None:
        change(next(iter(netlist_dict["modules"].values())))
    return YosysNetlist(**netlist_dict)


def test_unsupported_cell():
    circuit, counter, buttons = _counter()

    def weird_cell(module):
        next(iter(module["cells"].values()))["type"] = "$weird"

    netlist = _netlist(weird_cell)
    with pytest.raises(YosysComponentException, match="Unsupported Yosys cell '\\$weird'"):
        counter.check_netlist(netlist)
    with pytest.raises(YosysComponentException, match="Unsupported"):
        counter.reload_from_netlist(netlist)
    assert _counts(circuit, counter, buttons, 3)


def test_missing_state_signal():
    """A signal in 'states' that the new netlist doesn't have (renamed in the Verilog)"""
    circuit = Circuit()
    fsm = YosysComponent(circuit, path=FSM_PARAMETERS, signals=True, states="flag")
    circuit.init()
    cells = list(fsm._gates_comp._components)
    netlist_dict = copy.deepcopy(YosysComponent.synthesize_file(FSM_PARAMETERS))
    module = next(iter(netlist_dict["modules"].values()))
    module["netnames"]["renamed"] = module["netnames"].pop("flag")
    with pytest.raises(YosysComponentException, match="No signal 'flag'"):
        fsm.reload_from_netlist(YosysNetlist(**netlist_dict))
    # Not taken apart: the same cells, and the signals are there
    assert list(fsm._gates_comp._components) == cells
    assert fsm.state("flag") == "X"


def test_good_netlist_reloads():
    circuit, counter, buttons = _counter()
    counter.check_netlist(_netlist())
    counter.reload_from_netlist(_netlist())
    assert _counts(circuit, counter, buttons, 4)
