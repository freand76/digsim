# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""Test synthesizing Verilog with other values for the parameters of its module"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import platformdirs
import pytest

import digsim.circuit.components._yosys_component as yosys_component
from digsim.app._build_flow import run_synthesis, synth_step_name
from digsim.app._yosys_interface import load_netlists, parameter_column
from digsim.circuit import Circuit
from digsim.circuit.components import StaticValue, YosysComponent, YosysVariant
from digsim.circuit.components._yosys_component import YosysComponentException
from digsim.storage_model import ComponentDataClass
from digsim.synth import Synthesis, SynthesisException
from digsim.utils import YosysNetlist


VERILOG = Path(__file__).parent / "verilog" / "parameters.v"


@pytest.fixture(autouse=True)
def empty_cache():
    yosys_component._netlist_cache.clear()
    yield
    yosys_component._netlist_cache.clear()


@pytest.fixture(name="work_dir")
def fixture_work_dir():
    """A folder Yosys can read: YoWASP has a private /tmp"""
    cache_dir = Path(platformdirs.user_cache_dir("digsim", appauthor=False))
    cache_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=cache_dir, ignore_cleanup_errors=True) as work_dir:
        yield Path(work_dir)


def _widths(netlist_dict):
    ports = netlist_dict["modules"]["parameters"]["ports"]
    return {name: len(port["bits"]) for name, port in ports.items()}


def _outputs(component, a):
    """The outputs of a component of parameters.v for the input a"""
    circuit = component.circuit
    StaticValue(circuit, "A", width=component.a.width, value=a).O.wire = component.a
    circuit.init()
    circuit.run(ms=1)
    return component.y.value, component.offset.value, component.big.value


def test_defaults():
    netlist = Synthesis(VERILOG, "parameters").synth_to_dict(silent=True)
    assert _widths(netlist) == {"a": 4, "y": 4, "offset": 8, "big": 64}


@pytest.mark.parametrize("functional", [False, True])
def test_synthesis_with_parameters(functional):
    synthesis = Synthesis(
        VERILOG, "parameters", functional=functional, parameters={"WIDTH": 8, "OFFSET": 2}
    )
    assert _widths(synthesis.synth_to_dict(silent=True))["a"] == 8


@pytest.mark.parametrize("functional", [False, True])
def test_component_with_parameters(functional):
    """Negative values and values wider than 32 bits"""
    big = 0x0123_4567_89AB_CDEF
    component = YosysComponent(
        Circuit(),
        VERILOG,
        functional=functional,
        parameters={"WIDTH": 8, "OFFSET": -3, "BIG": big},
    )
    assert component.interface()["a"] == ("input", 8)
    assert _outputs(component, 0x01) == (0xFE, 0xFD, big)
    assert component.parameters == {"BIG": big, "OFFSET": -3, "WIDTH": 8}
    assert component.variant == YosysVariant(functional, f"BIG={big},OFFSET=-3,WIDTH=8")


def test_parameters_as_text():
    component = YosysComponent(Circuit(), VERILOG, parameters=" WIDTH = 0x8, OFFSET=-3 ")
    assert component.parameters == {"OFFSET": -3, "WIDTH": 8}
    assert component.interface()["a"] == ("input", 8)


@pytest.mark.parametrize(
    "parameters, message",
    [
        ({"WIDTH-1": 8}, "Not a parameter name"),
        ({"WIDTH": "8"}, "is not an integer"),
        ({"WIDTH": 8.0}, "is not an integer"),
    ],
)
def test_synthesis_refuses_bad_parameters(parameters, message):
    with pytest.raises(SynthesisException, match=message):
        Synthesis(VERILOG, "parameters", parameters=parameters)


def test_unknown_parameter_is_a_synthesis_error():
    with pytest.raises(SynthesisException, match="NOPE"):
        Synthesis(VERILOG, "parameters", parameters={"NOPE": 1}).synth_to_dict(silent=True)


@pytest.mark.parametrize(
    "parameters, message",
    [
        ("WIDTH", "Not a parameter: 'WIDTH'"),
        ("WIDTH=eight", "Not a parameter: 'WIDTH=eight'"),
        ({"WIDTH": "8"}, "is not an int"),
    ],
)
def test_component_refuses_bad_parameters(parameters, message):
    with pytest.raises(YosysComponentException, match=message):
        YosysComponent(Circuit(), VERILOG, parameters=parameters)


def test_netlist_file_has_no_parameters(work_dir):
    path = work_dir / "parameters.json"
    path.write_text(json.dumps(YosysComponent.synthesize_file(VERILOG)), encoding="utf-8")
    with pytest.raises(YosysComponentException, match="has no parameters"):
        YosysComponent(Circuit(), path, parameters={"WIDTH": 8})


def test_each_variant_is_cached(monkeypatch):
    count = [0]
    synth_to_dict = Synthesis.synth_to_dict

    def counting(self, silent=False):
        count[0] += 1
        return synth_to_dict(self, silent)

    monkeypatch.setattr(Synthesis, "synth_to_dict", counting)
    default = YosysComponent.synthesize_file(VERILOG)
    wide = YosysComponent.synthesize_file(VERILOG, parameters={"WIDTH": 8})
    assert count[0] == 2
    assert _widths(default)["a"] == 4 and _widths(wide)["a"] == 8
    circuit = Circuit()
    YosysComponent(circuit, VERILOG, parameters="WIDTH=8")
    YosysComponent(circuit, VERILOG)
    assert count[0] == 2


def test_parameters_are_saved():
    circuit = Circuit()
    component = YosysComponent(circuit, VERILOG, parameters={"WIDTH": 8, "OFFSET": -3})
    data = ComponentDataClass.from_component(component)
    assert data.settings["parameters"] == "OFFSET=-3,WIDTH=8"
    loaded = data.create(Circuit())
    assert isinstance(loaded, YosysComponent)
    assert loaded.parameters == {"OFFSET": -3, "WIDTH": 8}
    assert loaded.interface()["a"] == ("input", 8)


def test_no_parameters_are_not_saved():
    """A file without parameters can be read by DigSim from before them"""
    component = YosysComponent(Circuit(), VERILOG)
    assert "parameters" not in component.settings_to_dict()
    assert component.variant == YosysVariant(False, "")


def test_reconfigure_keeps_the_parameters():
    component = YosysComponent(Circuit(), VERILOG, parameters={"WIDTH": 8})
    component.update_settings({"functional": True})
    assert component.functional
    assert component.interface()["a"] == ("input", 8)
    assert _outputs(component, 0x01) == (0x02, 0x01, 0)


def test_given_netlists_by_variant():
    circuit = Circuit()
    wide = YosysComponent(circuit, VERILOG, parameters="WIDTH=8")
    given = [(VERILOG, wide.variant, wide.netlist())]
    with YosysComponent.given_netlists(given):
        # The default variant is synthesized, the other one gets the given netlist
        default = YosysComponent(circuit, VERILOG)
        second = YosysComponent(circuit, VERILOG, parameters="WIDTH=8")
    assert default.interface()["a"] == ("input", 4)
    assert second.interface()["a"] == ("input", 8)


def test_load_netlists_by_variant():
    wide = YosysVariant(True, "WIDTH=8")
    netlists = load_netlists(VERILOG, {YosysVariant(), wide})
    assert _widths(netlists[YosysVariant()])["a"] == 4
    assert _widths(netlists[wide])["a"] == 8
    assert YosysNetlist(**netlists[wide]).get_modules()


def test_build_steps_name_the_parameters():
    wide = YosysVariant(False, "OFFSET=2,WIDTH=8")
    assert synth_step_name(wide) == "Synthesize into gates (OFFSET=2, WIDTH=8)"
    steps = []
    result = run_synthesis(VERILOG, {YosysVariant(), wide}, steps.append)
    assert result.netlists is not None
    assert _widths(result.netlists[wide])["a"] == 8
    assert [step.name for step in steps if step.status == "ok"] == [
        "List modules",
        "Synthesize into gates",
        "Synthesize into gates (OFFSET=2, WIDTH=8)",
    ]


def test_command_line(work_dir):
    netlist = work_dir / "parameters.json"
    command = [sys.executable, "-m", "digsim.synth", "synth", "-s", "-i", str(VERILOG)]
    command += ["-o", str(netlist), "-t", "parameters", "-p", "WIDTH=8", "OFFSET=-3"]
    subprocess.run(command, check=True, capture_output=True)
    assert _widths(json.loads(netlist.read_text(encoding="utf-8")))["a"] == 8
    command[-3:] = ["-p", "WIDTH"]
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    assert result.returncode != 0
    assert "'WIDTH' is not NAME=VALUE" in result.stderr


def test_list_parameters(work_dir):
    assert Synthesis.list_parameters(VERILOG, "parameters") == {"WIDTH": 4, "OFFSET": 1, "BIG": 0}
    path = work_dir / "kinds.v"
    path.write_text(
        'module kinds #(parameter TEXT = "a b", parameter integer N = -5, '
        "parameter signed [7:0] S = -2, localparam L = 3) (output y);\n"
        "   assign y = N[0];\nendmodule\n",
        encoding="utf-8",
    )
    # A localparam is not a parameter that can be set
    assert Synthesis.list_parameters(path, "kinds") == {"TEXT": '"a b"', "N": -5, "S": -2}
    with pytest.raises(SynthesisException, match="No module 'other'"):
        Synthesis.list_parameters(path, "other")


def test_parameter_column():
    assert parameter_column({"WIDTH": " 8 ", "OFFSET": "", "BIG": "0x10"}) == "BIG=16,WIDTH=8"
    assert parameter_column({"WIDTH": "08", "OFFSET": "-3"}) == "OFFSET=-3,WIDTH=8"
    assert parameter_column({"WIDTH": ""}) == ""
    with pytest.raises(ValueError) as error:
        parameter_column({"WIDTH": "8", "OFFSET": "one"})
    assert error.value.args == ("OFFSET is not an integer: 'one'", "OFFSET")


def test_set_parameters(work_dir):
    component = YosysComponent(Circuit(), VERILOG)
    component.set_parameters({"WIDTH": 8})
    # Not built again: the netlist is the one from before, until it is reloaded
    assert component.interface()["a"] == ("input", 4)
    assert component.variant == YosysVariant(False, "WIDTH=8")
    component.set_parameters(None)
    assert component.parameters == {}
    path = work_dir / "parameters.json"
    path.write_text(json.dumps(YosysComponent.synthesize_file(VERILOG)), encoding="utf-8")
    with pytest.raises(YosysComponentException, match="has no parameters"):
        YosysComponent(Circuit(), path).set_parameters("WIDTH=8")


def test_list_module_parameters():
    other = Path(__file__).parent / "verilog" / "multiple_modules.v"
    modules = Synthesis.list_module_parameters([VERILOG, other])
    assert modules["parameters"] == {"WIDTH": 4, "OFFSET": 1, "BIG": 0}
    assert modules["multi_module_one"] == {}
    assert set(modules) == {
        "parameters",
        "multi_module_one",
        "multi_module_two",
        "multi_module_three",
    }


def test_command_line_lists_the_parameters():
    other = Path(__file__).parent / "verilog" / "one_module.v"
    command = [sys.executable, "-m", "digsim.synth", "list", "-i", str(VERILOG), str(other)]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    lines = result.stdout.splitlines()
    start = lines.index("0: module_one")
    assert lines[start : start + 5] == [
        "0: module_one",
        "1: parameters",
        "   WIDTH = 4",
        "   OFFSET = 1",
        "   BIG = 0",
    ]
