# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""Pystest module to test functionality of yosys synthesis"""

import os
import sys
from pathlib import Path

import pytest

from digsim.synth import (
    Synthesis,
    SynthesisException,
    YosysMessage,
    parse_messages,
    yosys_path_problem,
)
from digsim.synth._synthesis import _console_to_file


# Also on the other platforms: the minimal scope of the tests (see .github/workflows)
pytestmark = pytest.mark.sanity


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


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="/tmp is a folder on Linux")
def test_yosys_can_not_read_its_own_folders():
    """Files in /tmp and /share, or directly in /, get a message that says why"""
    assert "/tmp folder of its own" in yosys_path_problem("/tmp/design.v")
    assert "/tmp folder of its own" in yosys_path_problem("/tmp/../tmp/designs/design.v")
    assert "/share folder of its own" in yosys_path_problem("/share/designs/design.v")
    assert "directly in /" in yosys_path_problem("/design.v")
    with pytest.raises(SynthesisException, match="/tmp folder of its own"):
        Synthesis.list_modules("/tmp/design.v")
    with pytest.raises(SynthesisException, match="/tmp folder of its own"):
        Synthesis("/tmp/design.v", "design").synth_to_dict(silent=True)


def test_yosys_can_read_other_folders(verilog_path):
    """Files outside those folders can be read, and any file by a relative path"""
    assert yosys_path_problem(verilog_path / "one_module.v") is None
    assert yosys_path_problem("/tmpdir/design.v") is None
    assert yosys_path_problem("design.v") is None


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="/tmp is a folder on Linux")
def test_yosys_reads_relative_paths_in_tmp(verilog_path, tmp_path, monkeypatch):
    """YoWASP sees the working folder by relative paths, also in /tmp"""
    (tmp_path / "one_module.v").write_text((verilog_path / "one_module.v").read_text())
    monkeypatch.chdir(tmp_path)
    assert Synthesis.list_modules("one_module.v") == ["module_one"]


@pytest.mark.skipif(os.name == "nt", reason="links need extra rights on Windows")
def test_yosys_reads_through_links(verilog_path):
    """
    A file reached through a link to an absolute path is read by its real path: the
    WebAssembly Yosys doesn't follow such links
    """
    # Not in tmp_path: the WebAssembly Yosys can't read the system temp folder
    with Synthesis._work_dir() as work_dir:
        designs = work_dir / "designs"
        designs.mkdir()
        (designs / "one_module.v").write_text((verilog_path / "one_module.v").read_text())
        (work_dir / "file_link.v").symlink_to(designs / "one_module.v")
        (work_dir / "folder_link").symlink_to(designs)
        assert Synthesis.list_modules(work_dir / "file_link.v") == ["module_one"]
        assert Synthesis.list_modules(work_dir / "folder_link" / "one_module.v") == ["module_one"]


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="uses /proc to list open files")
def test_console_file_that_cannot_be_opened(tmp_path):
    """No file descriptors are left open when the console file can't be opened"""
    open_before = len(os.listdir("/proc/self/fd"))
    for _ in range(3):
        with pytest.raises(OSError), _console_to_file(tmp_path / "missing" / "console.txt"):
            pass
    assert len(os.listdir("/proc/self/fd")) == open_before


def test_parse_messages():
    log = [
        "/path/file.v:3: ERROR: syntax error, unexpected ';'",
        "C:/my files/file.v:2.5-2.9: Warning: Identifier `\\b' is implicitly declared.",
        "Warning: Wire t.\\y is used but has no driver.",
        "Warning: Wire t.\\y is used but has no driver.",
        "Warnings: 2 unique messages, 2 total",
        "ERROR: Module `\\top' not found!",
        "Something else",
    ]
    assert parse_messages(log) == [
        YosysMessage("error", "syntax error, unexpected ';'", "/path/file.v", 3),
        YosysMessage(
            "warning", "Identifier `\\b' is implicitly declared.", "C:/my files/file.v", 2
        ),
        YosysMessage("warning", "Wire t.\\y is used but has no driver."),
        YosysMessage("error", "Module `\\top' not found!"),
    ]


def test_yosys_syntax_error_messages(verilog_path):
    """A syntax error has its file and line, and the log"""
    log = []
    with pytest.raises(SynthesisException) as exc_info:
        Synthesis.list_modules(verilog_path / "syntax_error.v", log=log)
    exc = exc_info.value
    assert exc.log == log
    assert len(log) > 0
    error = exc.messages[-1]
    assert error.kind == "error"
    assert error.line == 4
    assert error.file is not None and error.file.endswith("syntax_error.v")
    assert "syntax error" in error.text


def test_yosys_error_without_log_is_a_message():
    exc = SynthesisException("ERROR: Yosys failed with exit code 1")
    assert exc.log == []
    assert exc.messages == [YosysMessage("error", "Yosys failed with exit code 1")]


def test_yosys_warnings(verilog_path):
    path = verilog_path / "module_with_warning.v"
    synthesis = Synthesis(path, "warning_module")
    synthesis.synth_to_dict(silent=True)
    messages = synthesis.get_messages()
    assert all(message.kind == "warning" for message in messages)
    assert any(message.line == 4 and "implicitly declared" in message.text for message in messages)
    assert any(message.line is None and "y2" in message.text for message in messages)


def _options_netlist(verilog_path, **arguments):
    """The ports and cells of tests/verilog/cocotb_options.sv, synthesized"""
    synthesis = Synthesis(str(verilog_path / "cocotb_options.sv"), "options", **arguments)
    module = synthesis.synth_to_dict(silent=True)["modules"]["options"]
    cells = sorted({cell["type"] for cell in module["cells"].values()})
    return len(module["ports"]["a"]["bits"]), cells


def test_yosys_includes_and_defines(verilog_path):
    """Files are included from the include folders, macros are defined with or without a value"""
    include = verilog_path / "include"
    assert _options_netlist(verilog_path, includes=[include]) == (2, [])
    assert _options_netlist(verilog_path, includes=[include], defines={"INVERT": None}) == (
        2,
        ["$_NOT_"],
    )
    assert _options_netlist(
        verilog_path,
        includes=[str(include)],
        defines={"INVERT": 1, "OTHER": "8'd3"},
        parameters={"WIDTH": 4},
    ) == (4, ["$_NOT_"])


def test_yosys_include_missing(verilog_path):
    """Without the include folder, Yosys can't find the included file"""
    with pytest.raises(SynthesisException, match="cocotb_options.vh"):
        _options_netlist(verilog_path)


@pytest.mark.parametrize(
    "arguments, message",
    [
        ({"defines": {"1X": 1}}, "Not a macro name"),
        ({"defines": {"X": "a\nb"}}, "has a line break"),
        ({"defines": {"X": "a\\"}}, "has a line break"),
        ({"includes": ["include folder"]}, "include folder"),
    ],
)
def test_yosys_bad_includes_and_defines(verilog_path, arguments, message):
    """Macros and include folders that Yosys can't be given are errors at once"""
    with pytest.raises(SynthesisException, match=message):
        Synthesis(str(verilog_path / "cocotb_options.sv"), "options", **arguments)


STRING_MACRO = '"path/to/some (random quote)/a;b#c.wow"'


def _string_macro_value(verilog_path, text):
    """y of tests/verilog/synth_string_macro.sv, with the macro TEXT"""
    synthesis = Synthesis(
        str(verilog_path / "synth_string_macro.sv"), "string_macro", defines={"TEXT": text}
    )
    module = synthesis.synth_to_dict(silent=True)["modules"]["string_macro"]
    return module["ports"]["y"]["bits"]


def test_yosys_string_macro(verilog_path):
    """A string macro keeps its quotes, spaces, semicolon and #, like a `define in a file"""
    assert _string_macro_value(verilog_path, STRING_MACRO) == ["1", "0"]
    assert _string_macro_value(verilog_path, '"other"') == ["0", "1"]
