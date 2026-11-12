# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""A Verilog file with several modules: its top module, or the module that is chosen"""

import json
import tempfile
from pathlib import Path

import platformdirs
import pytest

from digsim.app._build_flow import run_synthesis
from digsim.app._settings_values import (
    MODULE_PARAMETER,
    module_parameter,
    new_module_choices,
    pane_parameters,
)
from digsim.circuit import Circuit
from digsim.circuit.components import (
    StaticValue,
    VerilogComponent,
    YosysComponent,
    YosysComponentException,
    YosysVariant,
)
from digsim.synth import Synthesis


# Also on the other platforms: files and Yosys (see .github/workflows)
pytestmark = pytest.mark.sanity


VERILOG = Path(__file__).parent.parent / "verilog"
HIERARCHY = VERILOG / "hierarchy.v"
MULTIPLE = VERILOG / "multiple_modules.v"
MULTIPLE_MODULES = ["multi_module_one", "multi_module_two", "multi_module_three"]


@pytest.fixture(name="work_dir")
def fixture_work_dir():
    """A folder Yosys can read: YoWASP has a private /tmp"""
    cache_dir = Path(platformdirs.user_cache_dir("digsim", appauthor=False))
    cache_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=cache_dir, ignore_cleanup_errors=True) as work_dir:
        yield Path(work_dir)


def _drive(circuit, component, **values):
    """Static values on inputs of a component, by port name"""
    for name, value in values.items():
        port = component.port(name)
        static = StaticValue(circuit, f"in_{name}", width=port.width, value=value)
        static.O.wire = port


def test_module_hierarchy():
    """The modules in the order of the file, with the modules that they instantiate"""
    hierarchy = Synthesis.module_hierarchy(HIERARCHY)
    assert hierarchy == {"half_adder": [], "adder": [], "top": ["half_adder", "adder"]}
    assert Synthesis.top_modules(hierarchy) == ["top"]
    assert Synthesis.top_modules(Synthesis.module_hierarchy(MULTIPLE)) == MULTIPLE_MODULES


@pytest.mark.parametrize("functional", [False, True])
def test_top_module(functional):
    """The component is the top module, with its submodules in it"""
    circuit = Circuit()
    top = VerilogComponent(circuit, HIERARCHY, functional=functional)
    assert top.name() == "top"
    assert top.module == ""
    assert sorted(top.interface()) == ["a", "b", "c", "s", "sum", "x"]
    _drive(circuit, top, a=1, b=1, x=11)
    circuit.init()
    circuit.run(ms=1)
    assert (top.s.value, top.c.value, top.sum.value) == (0, 1, 22)
    assert "module" not in top.settings_to_dict()


@pytest.mark.parametrize("functional", [False, True])
def test_submodule(functional):
    """A module of the file, instead of the top module"""
    circuit = Circuit()
    adder = VerilogComponent(
        circuit, HIERARCHY, module="adder", functional=functional, parameters="WIDTH=3"
    )
    assert adder.name() == "adder"
    assert adder.module_name() == "adder"
    assert adder.interface() == {"x": ("input", 3), "y": ("input", 3), "sum": ("output", 4)}
    _drive(circuit, adder, x=5, y=6)
    circuit.init()
    circuit.run(ms=1)
    assert adder.sum.value == 11
    assert adder.variant == YosysVariant(functional, "WIDTH=3", "adder")


def test_several_top_modules():
    """The modules don't instantiate each other: one of them is chosen"""
    with pytest.raises(YosysComponentException, match=r"3 top modules \(multi_module_one, "):
        VerilogComponent(Circuit(), MULTIPLE)
    two = VerilogComponent(Circuit(), MULTIPLE, module="multi_module_two")
    assert two.name() == "multi_module_two"
    assert sorted(two.interface()) == ["clk", "cnt", "reset"]


def test_no_such_module(work_dir):
    with pytest.raises(YosysComponentException, match="No module 'nope' in 'hierarchy.v'"):
        VerilogComponent(Circuit(), HIERARCHY, module="nope")
    # A netlist is made from its one module
    netlist = work_dir / "half_adder.json"
    netlist.write_text(
        json.dumps(YosysComponent.synthesize_file(HIERARCHY, module="half_adder")),
        encoding="utf-8",
    )
    with pytest.raises(YosysComponentException, match="not a Verilog file"):
        VerilogComponent(Circuit(), netlist, module="half_adder")


def test_save_and_load(work_dir):
    """The module is saved, a circuit with it loads"""
    circuit = Circuit(name="modules")
    VerilogComponent(circuit, MULTIPLE, module="multi_module_three")
    VerilogComponent(circuit, HIERARCHY)
    path = work_dir / "modules.circuit"
    circuit.to_json_file(path)
    loaded = Circuit()
    loaded.from_json_file(path)
    three = loaded.get_component("multi_module_three")
    assert isinstance(three, VerilogComponent)
    assert three.settings_to_dict()["module"] == "multi_module_three"
    assert loaded.get_component("top").module == ""


def test_build_flow():
    """The editor synthesizes the module of each component, or says to choose one"""
    variants = {
        YosysVariant(module="multi_module_two"),
        YosysVariant(True, "", "multi_module_one"),
    }
    steps = []
    result = run_synthesis(MULTIPLE, variants, steps.append)
    assert [
        (step.name, step.status, step.detail) for step in steps if step.status != "running"
    ] == [
        ("List modules", "ok", "Modules multi_module_one, multi_module_two"),
        ("Synthesize into gates (module multi_module_two)", "ok", ""),
        ("Synthesize into functional blocks (module multi_module_one)", "ok", ""),
    ]
    assert result.netlists is not None
    assert set(result.netlists) == variants
    result = run_synthesis(HIERARCHY, {YosysVariant()}, steps.append)
    assert steps[-1].detail == ""
    assert steps[-3].detail == "Module top"


def test_settings_pane(work_dir):
    """The pane has the module of a component from a file with several modules"""
    circuit = Circuit()
    top = VerilogComponent(circuit, HIERARCHY)
    parameter = module_parameter(top)
    assert parameter is not None
    assert parameter["items"] == ["top", "half_adder", "adder"]
    assert parameter["default"] == "top"
    parameters = pane_parameters(top, circuit)
    assert list(parameters).index(MODULE_PARAMETER) == list(parameters).index("path") + 1
    # One module: nothing to choose
    one = VerilogComponent(circuit, VERILOG / "one_module.v")
    assert module_parameter(one) is None
    assert MODULE_PARAMETER not in pane_parameters(one, circuit)
    # A new component asks for the module when there are several top modules, from the
    # same list: the top modules first
    assert new_module_choices(str(MULTIPLE)) == MULTIPLE_MODULES
    assert new_module_choices(str(HIERARCHY)) == []
    assert new_module_choices(str(VERILOG / "syntax_error.v")) == []
    two_tops = work_dir / "two_tops.v"
    other = "module other (input a, output y);\n  assign y = ~a;\nendmodule\n"
    two_tops.write_text(HIERARCHY.read_text(encoding="utf-8") + other, encoding="utf-8")
    choices = new_module_choices(str(two_tops))
    assert choices == ["top", "other", "half_adder", "adder"]
    other_component = VerilogComponent(circuit, two_tops, module="other")
    parameter = module_parameter(other_component)
    assert parameter is not None
    assert parameter["items"] == choices
