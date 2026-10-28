# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""Test the Verilog formatter"""

from pathlib import Path

import pytest

import digsim.verilog._formatter
from digsim.verilog import VerilogFormatError, VerilogFormatter
from digsim.verilog.__main__ import main


# Also on the other platforms: the minimal scope of the tests (see .github/workflows)
pytestmark = pytest.mark.sanity


ROOT = Path(__file__).parent.parent
VERILOG_FILES = sorted(
    [*ROOT.glob("examples/**/*.v"), *ROOT.glob("examples/**/*.sv"), *ROOT.glob("tests/**/*.v")]
)


def _format(text, **kwargs):
    return VerilogFormatter(**kwargs).format(text)


def _lines(*lines):
    return "\n".join(lines) + "\n"


def test_module_and_blocks():
    text = _lines(
        "module m(input clk, output reg q);",
        "always @(posedge clk) begin",
        "if (q) begin",
        "q <= 0;",
        "end else begin",
        "q <= 1;",
        "end",
        "end",
        "endmodule",
    )
    assert _format(text) == _lines(
        "module m(input clk, output reg q);",
        "    always @(posedge clk) begin",
        "        if (q) begin",
        "            q <= 0;",
        "        end else begin",
        "            q <= 1;",
        "        end",
        "    end",
        "endmodule",
    )


def test_indent_size():
    assert _format("module m;\nwire a;\nendmodule\n", indent=3) == _lines(
        "module m;", "   wire a;", "endmodule"
    )


def test_case():
    text = _lines("case (s)", "2'd0: y = a;", "default: begin", "y = b;", "end", "endcase")
    assert _format(text) == _lines(
        "case (s)",
        "    2'd0: y = a;",
        "    default: begin",
        "        y = b;",
        "    end",
        "endcase",
    )


def test_brackets():
    text = _lines(
        "module m (",
        "input a,",
        "output y",
        ");",
        "assign y = {a,",
        "a};",
        "endmodule",
    )
    assert _format(text) == _lines(
        "module m (",
        "    input a,",
        "    output y",
        ");",
        "    assign y = {a,",
        "        a};",
        "endmodule",
    )


def test_two_brackets_on_one_line_indent_one_step():
    text = _lines("assign y = f({", "a, b", "});")
    assert _format(text) == _lines("assign y = f({", "    a, b", "});")


def test_statement_continues_on_next_line():
    text = _lines("if (a)", "x = 1;", "else", "x = 2;", "assign y = a &", "b;", "wire c;")
    assert _format(text) == _lines(
        "if (a)", "    x = 1;", "else", "    x = 2;", "assign y = a &", "    b;", "wire c;"
    )


def test_begin_on_its_own_line():
    text = _lines("always @(posedge clk)", "begin", "q <= d;", "end", "wire a;")
    assert _format(text) == _lines(
        "always @(posedge clk)", "    begin", "        q <= d;", "    end", "wire a;"
    )


def test_named_blocks():
    text = _lines("begin : name", "a = 1;", "end : name", "wire b;")
    assert _format(text) == _lines("begin : name", "    a = 1;", "end : name", "wire b;")


@pytest.mark.parametrize(
    "line",
    [
        "extern function int f();",
        'import "DPI-C" function int f();',
        "wait fork;",
        "disable fork;",
        "assert property (a);",
        "typedef class c;",
    ],
)
def test_keywords_that_open_no_block(line):
    text = _lines("module m;", line, "wire a;", "endmodule")
    assert _format(text) == _lines("module m;", "    " + line, "    wire a;", "endmodule")


def test_comments_are_indented_like_code():
    text = _lines("module m;", "// a", "  wire a; //  b  ", "endmodule")
    assert _format(text) == _lines("module m;", "    // a", "    wire a; //  b", "endmodule")


def test_block_comment_lines_move_with_the_first():
    text = _lines("module m;", "/* a", "   b", "*/", "wire a;", "endmodule")
    assert _format(text) == _lines(
        "module m;", "    /* a", "       b", "    */", "    wire a;", "endmodule"
    )
    # Moved left, but not into the text of the comment
    text = _lines("        /* a", "  b */")
    assert _format(text) == _lines("/* a", "b */")


def test_define_continuation_kept():
    text = _lines("module m;", "`define MAX(a, b) \\", "  ((a) > (b) ? (a) : (b))", "endmodule")
    assert _format(text) == _lines(
        "module m;", "    `define MAX(a, b) \\", "  ((a) > (b) ? (a) : (b))", "endmodule"
    )


def test_directives_dont_change_the_indentation():
    text = _lines("module m;", "`ifdef A", "wire a;", "`endif", "wire b;", "endmodule")
    assert _format(text) == _lines(
        "module m;", "    `ifdef A", "    wire a;", "    `endif", "    wire b;", "endmodule"
    )


def test_whitespace():
    text = "\n\n\tmodule m;  \n\n\n\n\twire a;\t\nendmodule"
    assert _format(text) == _lines("module m;", "", "    wire a;", "endmodule")
    assert _format(text, blank_lines=2) == _lines("module m;", "", "", "    wire a;", "endmodule")


def test_crlf_kept():
    assert _format("module m;\r\nwire a;\r\nendmodule\r\n") == (
        "module m;\r\n    wire a;\r\nendmodule\r\n"
    )


def test_empty():
    assert _format("") == ""
    assert _format("\n \n") == ""


def test_unbalanced_code_is_formatted():
    """Code with errors is formatted as far as it goes, it is not checked"""
    text = _lines("end", "endmodule", "begin", "a;")
    assert _format(text) == _lines("end", "endmodule", "begin", "    a;")


def test_changed_tokens_are_not_formatted(monkeypatch):
    """The formatter checks that the code is the same, a bug in it changes nothing"""
    original = VerilogFormatter._format_lines
    monkeypatch.setattr(
        VerilogFormatter,
        "_format_lines",
        lambda self, lines: [line.replace("a", "b") for line in original(self, lines)],
    )
    with pytest.raises(VerilogFormatError):
        _format("wire a;\n")


def test_strings_kept():
    text = _lines("initial", '$display("  a  ");')
    assert _format(text) == _lines("initial", '    $display("  a  ");')


@pytest.mark.parametrize("path", VERILOG_FILES, ids=lambda path: path.name)
def test_files_format_twice_the_same(path):
    text = path.read_text(encoding="utf-8")
    formatted = _format(text)
    assert _format(formatted) == formatted


def test_main_check_and_in_place(tmp_path, capsys):
    path = tmp_path / "m.v"
    path.write_text("module m;\nwire a;\nendmodule\n", encoding="utf-8")
    assert main(["format", "--check", str(path)]) == 1
    assert "Would format" in capsys.readouterr().out
    assert main(["format", "-i", str(path)]) == 0
    assert path.read_text(encoding="utf-8") == "module m;\n    wire a;\nendmodule\n"
    assert main(["format", "--check", str(path)]) == 0


def test_main_stdout(tmp_path, capsys):
    path = tmp_path / "m.v"
    path.write_text("module m;\nwire a;\nendmodule\n", encoding="utf-8")
    assert main(["format", "--indent", "2", str(path)]) == 0
    assert capsys.readouterr().out == "module m;\n  wire a;\nendmodule\n"
    # Not written back
    assert path.read_text(encoding="utf-8") == "module m;\nwire a;\nendmodule\n"


def test_main_stdout_of_windows_newlines(tmp_path, capsys):
    """The newlines of a file with \r\n are written as \n, the system's text mode makes them"""
    path = tmp_path / "m.v"
    path.write_bytes(b"module m;\r\nwire a;\r\nendmodule\r\n")
    assert main(["format", "--indent", "2", str(path)]) == 0
    assert capsys.readouterr().out == "module m;\n  wire a;\nendmodule\n"


def test_main_errors(tmp_path, capsys, monkeypatch):
    assert main(["format", str(tmp_path / "missing.v")]) == 2
    assert "ERROR" in capsys.readouterr().err
    path = tmp_path / "m.v"
    path.write_text("  wire a;\n", encoding="utf-8")
    # As if formatting changed the code
    monkeypatch.setattr(digsim.verilog._formatter, "_same_tokens", lambda text: [text])
    assert main(["format", "-i", str(path)]) == 2
    assert path.read_text(encoding="utf-8") == "  wire a;\n"


def test_non_breaking_spaces():
    """Text pasted from a web page: non-breaking spaces are indentation and spaces"""
    text = "module m;\n\u00a0\u00a0wire\u00a0a;\nendmodule\n"
    assert _format(text) == "module m;\n    wire\u00a0a;\nendmodule\n"


def test_main_formats_the_other_files_after_an_error(tmp_path, capsys):
    """A file that can't be read doesn't stop the other files"""
    good = tmp_path / "good.v"
    good.write_text("module m;\nwire\u00a0a;\nendmodule\n", encoding="utf-8")
    bad = tmp_path / "bad.v"
    bad.write_bytes(b"module m; // \xa9\nendmodule\n")
    assert main(["format", "-i", str(bad), str(good)]) == 2
    assert good.read_text(encoding="utf-8") == "module m;\n    wire\u00a0a;\nendmodule\n"
