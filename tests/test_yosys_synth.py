# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Pystest module to test functionality of yosys synthesis"""

from pathlib import Path

import pytest

from digsim.synth import Synthesis, SynthesisException


@pytest.fixture
def verilog_path():
    """Fixture: get path to verilog modules"""
    # Get the relative path to example folder
    test_path = Path(__file__).resolve().relative_to(Path.cwd())
    return Path(test_path).parent / "verilog"


def test_yosys_list_modules_single_files(verilog_path):
    """test list modules in single file (with single module)"""
    modules = Synthesis.list_modules(str(verilog_path / "one_module.v"))
    assert len(modules) == 1
    assert "module_one" in modules


def test_yosys_list_modules_multiple_files(verilog_path):
    """test list modules in multiple files (with single module)"""
    modules = Synthesis.list_modules(
        [str(verilog_path / "one_module.v"), str(verilog_path / "another_module.v")]
    )
    assert len(modules) == 2
    assert "module_one" in modules
    assert "module_two" in modules


def test_yosys_list_multiple_modules_single_file(verilog_path):
    """test list modules in single file (with multiple modules)"""
    modules = Synthesis.list_modules([str(verilog_path / "multiple_modules.v")])

    assert len(modules) == 3

    assert "multi_module_one" in modules
    assert "multi_module_two" in modules
    assert "multi_module_three" in modules


def test_yosys_list_module_with_error(verilog_path):
    """test list modules in single file (with multiple modules)"""

    with pytest.raises(SynthesisException):
        Synthesis.list_modules([str(verilog_path / "module_with_error.v")])


def test_yosys_synth_single_file_single_module(verilog_path):
    """test synth single file (with single module)"""
    synthesis = Synthesis(str(verilog_path / "one_module.v"), "module_one")
    netlist_dict = synthesis.synth_to_dict()
    assert "modules" in netlist_dict
    assert "module_one" in netlist_dict["modules"]


def test_yosys_synth_single_file_multi_modules(verilog_path):
    """test synth single file (with multiple modules)"""
    synthesis = Synthesis(str(verilog_path / "multiple_modules.v"), "multi_module_one")
    netlist_dict = synthesis.synth_to_dict()
    assert "modules" in netlist_dict
    assert "multi_module_one" in netlist_dict["modules"]

    synthesis = Synthesis(str(verilog_path / "multiple_modules.v"), "multi_module_two")
    netlist_dict = synthesis.synth_to_dict()
    assert "modules" in netlist_dict
    assert "multi_module_two" in netlist_dict["modules"]


def test_yosys_synth_module_with_error(verilog_path):
    """test list modules in single file (with multiple modules)"""

    synthesis = Synthesis(str(verilog_path / "module_with_error.v"), "error_module")

    with pytest.raises(SynthesisException):
        synthesis.synth_to_dict()
