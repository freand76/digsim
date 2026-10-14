# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Pystest module to test functionality of yosys synthesis"""

import os
import sys
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


def test_yosys_path_objects(verilog_path):
    """test that pathlib.Path arguments are accepted, not only strings"""
    modules = Synthesis.list_modules(verilog_path / "one_module.v")
    assert modules == ["module_one"]
    synthesis = Synthesis(verilog_path / "one_module.v", "module_one")
    netlist_dict = synthesis.synth_to_dict()
    assert "module_one" in netlist_dict["modules"]
    synthesis = Synthesis([verilog_path / "one_module.v"], "module_one")
    netlist_dict = synthesis.synth_to_dict()
    assert "module_one" in netlist_dict["modules"]


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="uses /proc to list open files")
def test_yosys_error_closes_files(verilog_path):
    """Yosys files are closed after an error (on Windows, open files cannot be deleted)"""
    with pytest.raises(SynthesisException):
        Synthesis.list_modules([str(verilog_path / "module_with_error.v")])
    open_files = []
    for fd in os.listdir("/proc/self/fd"):
        try:
            open_files.append(os.readlink(f"/proc/self/fd/{fd}"))
        except OSError:
            continue
    assert not [name for name in open_files if "yosys.log" in name]


def test_yosys_path_with_space(verilog_path):
    """Verilog files in a folder with a space in the name can be read"""
    # Not in tmp_path: the WebAssembly Yosys can't read the system temp folder
    with Synthesis._work_dir() as work_dir:
        folder = work_dir / "my designs"
        folder.mkdir()
        verilog_file = folder / "one_module.v"
        verilog_file.write_text((verilog_path / "one_module.v").read_text())
        assert Synthesis.list_modules(verilog_file) == ["module_one"]
        netlist_dict = Synthesis(verilog_file, "module_one").synth_to_dict(silent=True)
        assert "module_one" in netlist_dict["modules"]
