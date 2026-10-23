# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""Test the text operations of the Verilog editor"""

import pytest

from digsim.app._editor_text import (
    indent_lines,
    matching_bracket,
    module_name,
    new_line_indent,
    new_module_text,
    toggle_comment,
    unindent_lines,
)
from digsim.verilog import VerilogFormatter


def test_indent_lines():
    assert indent_lines(["a", "", "  b"], 4) == ["    a", "", "      b"]


def test_unindent_lines():
    assert unindent_lines(["      a", "  b", "c", "\tc"], 4) == ["  a", "b", "c", "c"]


def test_toggle_comment_adds_at_the_least_indentation():
    assert toggle_comment(["    a;", "", "  b;"]) == ["  //   a;", "", "  // b;"]


def test_toggle_comment_removes():
    assert toggle_comment(["  // a;", "", "  //b;"]) == ["  a;", "", "  b;"]
    # Not all lines are comments: they are commented
    assert toggle_comment(["// a;", "b;"]) == ["// // a;", "// b;"]


def test_toggle_comment_empty():
    assert toggle_comment(["", "  "]) == ["", "  "]


@pytest.mark.parametrize(
    ("line", "indent"),
    [
        ("    assign y = a;", "    "),
        ("    always @(posedge clk) begin", "        "),
        ("module m (", "    "),
        ("  case (s)", "      "),
        ("    end // begin", "    "),
        ("    x = f(a,", "        "),
        ("    x = f(a, b);", "    "),
        ("    // begin", "    "),
        ("", ""),
    ],
)
def test_new_line_indent(line, indent):
    assert new_line_indent(line, 4) == indent


def test_matching_bracket():
    text = "a = f(b[1], {c}); // (\n)"
    assert matching_bracket(text, 5) == (5, 15)
    # Just after the bracket
    assert matching_bracket(text, 16) == (15, 5)
    assert matching_bracket(text, 7) == (7, 9)
    assert matching_bracket(text, 12) == (12, 14)
    # Not a bracket, a bracket in a comment, and one without a match
    assert matching_bracket(text, 2) is None
    assert matching_bracket(text, text.index("//") + 4) is None
    assert matching_bracket(text, len(text)) is None


def test_matching_bracket_over_lines():
    text = "module m (\n    input a\n);"
    assert matching_bracket(text, 9) == (9, text.index(")"))


def test_new_module_text_is_formatted():
    text = new_module_text("blinky")
    assert text.startswith("module blinky (")
    assert VerilogFormatter().format(text) == text


@pytest.mark.parametrize(
    ("line", "indent"),
    [("end else begin", "    "), ("begin x = 1; end", ""), ("module m;", "    ")],
)
def test_new_line_indent_blocks(line, indent):
    assert new_line_indent(line, 4) == indent


@pytest.mark.parametrize(
    ("file_name", "name"),
    [
        ("blinky.v", "blinky"),
        ("my-counter 2.sv", "my_counter_2"),
        ("7seg.v", "m_7seg"),
        ("and.v", "m_and"),
        ("wire.v", "m_wire"),
        ("module.sv", "m_module"),
    ],
)
def test_module_name(file_name, name):
    assert module_name(file_name) == name
