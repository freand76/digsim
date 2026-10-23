# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""Test the Verilog lexer"""

import ast
from pathlib import Path

import pytest

from digsim.verilog import LexState, TokenKind, tokenize, tokenize_line


def _kinds(text):
    return [(token.kind, token.text) for token in tokenize(text) if token.kind != "whitespace"]


@pytest.mark.parametrize(
    "number",
    ["8'hFF", "4'b10xz", "'b01", "4'sb0001", "8'd255", "1'bx", "16'h DEAD", "'0", "'1", "'z"]
    + ["42", "1_000", "1.5", "2.5e-3", "10ns", "1s", "3'o7"],
)
def test_numbers(number):
    assert _kinds(number) == [(TokenKind.NUMBER, number)]


def test_keywords_identifiers_and_system_tasks():
    assert _kinds("module counter_1; $display(x$y); endmodule") == [
        (TokenKind.KEYWORD, "module"),
        (TokenKind.IDENTIFIER, "counter_1"),
        (TokenKind.OPERATOR, ";"),
        (TokenKind.SYSTEM, "$display"),
        (TokenKind.OPERATOR, "("),
        (TokenKind.IDENTIFIER, "x$y"),
        (TokenKind.OPERATOR, ")"),
        (TokenKind.OPERATOR, ";"),
        (TokenKind.KEYWORD, "endmodule"),
    ]


def test_escaped_identifier():
    assert _kinds("\\bus[0] + a") == [
        (TokenKind.IDENTIFIER, "\\bus[0]"),
        (TokenKind.OPERATOR, "+"),
        (TokenKind.IDENTIFIER, "a"),
    ]


def test_operators_longest_first():
    texts = [text for _, text in _kinds("a <<<= b >>> c === d !== e ~^ f +: g -> h ** i")]
    assert texts[0::2] == list("abcdefghi")
    assert texts[1::2] == [
        "<<<=",
        ">>>",
        "===",
        "!==",
        "~^",
        "+:",
        "->",
        "**",
    ]


def test_string_with_escaped_quote():
    assert _kinds('$display("a \\"b\\" // c");') == [
        (TokenKind.SYSTEM, "$display"),
        (TokenKind.OPERATOR, "("),
        (TokenKind.STRING, '"a \\"b\\" // c"'),
        (TokenKind.OPERATOR, ")"),
        (TokenKind.OPERATOR, ";"),
    ]


def test_comments():
    assert _kinds("a; // b /* c */") == [
        (TokenKind.IDENTIFIER, "a"),
        (TokenKind.OPERATOR, ";"),
        (TokenKind.COMMENT, "// b /* c */"),
    ]
    assert _kinds("a /* b */ c") == [
        (TokenKind.IDENTIFIER, "a"),
        (TokenKind.COMMENT, "/* b */"),
        (TokenKind.IDENTIFIER, "c"),
    ]


def test_block_comment_over_lines():
    tokens, state = tokenize_line("a /* b", LexState.CODE)
    assert state == LexState.BLOCK_COMMENT
    assert tokens[-1].kind == TokenKind.COMMENT
    tokens, state = tokenize_line("  still comment", state)
    assert state == LexState.BLOCK_COMMENT
    assert [token.kind for token in tokens] == [TokenKind.COMMENT]
    tokens, state = tokenize_line("end */ wire", state)
    assert state == LexState.CODE
    assert [(token.kind, token.text) for token in tokens] == [
        (TokenKind.COMMENT, "end */"),
        (TokenKind.WHITESPACE, " "),
        (TokenKind.KEYWORD, "wire"),
    ]


def test_directives():
    assert _kinds("`timescale 1ns/1ps") == [
        (TokenKind.DIRECTIVE, "`timescale"),
        (TokenKind.NUMBER, "1ns"),
        (TokenKind.OPERATOR, "/"),
        (TokenKind.NUMBER, "1ps"),
    ]
    # A macro is a directive token too
    assert _kinds("x = `WIDTH;")[2] == (TokenKind.DIRECTIVE, "`WIDTH")


def test_define_continued_with_backslash():
    tokens, state = tokenize_line("`define MAX(a, b) \\", LexState.CODE)
    assert [token.kind for token in tokens] == [TokenKind.DIRECTIVE]
    assert state == LexState.DEFINE
    tokens, state = tokenize_line("  ((a) > (b) ? (a) : (b))", state)
    assert [token.kind for token in tokens] == [TokenKind.DIRECTIVE]
    assert state == LexState.CODE


def test_positions():
    tokens = tokenize("a\n  b")
    assert [(token.text, token.line, token.column) for token in tokens] == [
        ("a", 0, 0),
        ("  ", 1, 0),
        ("b", 1, 2),
    ]


def test_tokens_cover_the_text():
    """Every character is in a token, also of text that isn't Verilog"""
    text = "module m; ¤ # @ ` 'q \" unclosed\n/* open"
    lines = text.split("\n")
    for number, line in enumerate(lines):
        joined = "".join(token.text for token in tokenize(text) if token.line == number)
        assert joined == line


def test_no_digsim_imports():
    """digsim.verilog uses only the standard library, it can become a package of its own"""
    folder = Path(__file__).parent.parent / "src" / "digsim" / "verilog"
    for path in folder.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom):
                assert node.level == 1 or not (node.module or "").startswith("digsim"), path
            elif isinstance(node, ast.Import):
                assert not any(alias.name.startswith("digsim") for alias in node.names), path


@pytest.mark.parametrize("space", ["\u00a0", "\u3000", "\u2028", "\x1c", "\u0085"])
def test_unicode_whitespace(space):
    """Whitespace from pasted text, like a non-breaking space, is whitespace"""
    assert _kinds(f"wire{space}a;") == [
        (TokenKind.KEYWORD, "wire"),
        (TokenKind.IDENTIFIER, "a"),
        (TokenKind.OPERATOR, ";"),
    ]


def test_every_character_is_a_token():
    """Characters that are no Verilog, like control characters, don't stop the lexer"""
    text = "a\x00b\x7f\u200bc"
    assert "".join(token.text for token in tokenize(text)) == text
