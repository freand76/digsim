# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""Test the faces of Verilog tokens for syntax highlighting"""

from digsim.app._verilog_faces import Face, faces
from digsim.verilog import tokenize_line


def _faces(line):
    tokens, _ = tokenize_line(line)
    return [(token.text, face) for token, face in faces(tokens)]


def test_module():
    assert _faces("module counter(input clk, output reg [3:0] cnt); // A counter") == [
        ("module", Face.KEYWORD),
        ("counter", Face.NAME),
        ("input", Face.TYPE),
        ("output", Face.TYPE),
        ("reg", Face.TYPE),
        ("3", Face.CONSTANT),
        ("0", Face.CONSTANT),
        ("// A counter", Face.COMMENT),
    ]


def test_statements():
    assert _faces('always @(posedge clk) if (x) $display("%d", 8\'hFF);') == [
        ("always", Face.KEYWORD),
        ("@", Face.TYPE),
        ("posedge", Face.KEYWORD),
        ("if", Face.KEYWORD),
        ("$display", Face.BUILTIN),
        ('"%d"', Face.STRING),
        ("8'hFF", Face.CONSTANT),
    ]


def test_function_name_after_types():
    assert ("f", Face.NAME) in _faces("function automatic [3:0] f(input a);")
    assert ("g", Face.NAME) in _faces("task g;")


def test_no_name_after_a_semicolon():
    """A module without a name on its line: the next identifier is no name"""
    assert ("x", Face.NAME) not in _faces("module; x")


def test_labels():
    assert _faces("begin : count end : count") == [
        ("begin", Face.KEYWORD),
        ("count", Face.CONSTANT),
        ("end", Face.KEYWORD),
        ("count", Face.CONSTANT),
    ]
    # A case item is no label
    assert ("RED", Face.CONSTANT) not in _faces("RED: state <= GREEN;")


def test_directives_and_macros():
    assert _faces("`define WIDTH 8") == [("`define WIDTH 8", Face.DIRECTIVE)]
    assert _faces("wire [`WIDTH-1:0] a;")[1] == ("`WIDTH", Face.DIRECTIVE)


def test_event_controls_and_delays():
    assert _faces("always @* #10 x = #5 y;") == [
        ("always", Face.KEYWORD),
        ("@", Face.TYPE),
        ("#", Face.TYPE),
        ("10", Face.TYPE),
        ("#", Face.TYPE),
        ("5", Face.TYPE),
    ]
