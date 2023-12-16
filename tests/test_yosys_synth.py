# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

""" Pystest module to test functionality of yosys synthesis """

# pylint: disable=redefined-outer-name

from pathlib import Path

import pytest
from digsim.synth import Synthesis


@pytest.fixture
def verilog_path():
    """Fixture: get path to verilog modules"""
    return Path(__file__).parent / "verilog"


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
