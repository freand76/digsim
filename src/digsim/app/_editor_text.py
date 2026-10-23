# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""
The text operations of the Verilog editor, on lines and positions. No Qt, so that they
can be tested.
"""

from __future__ import annotations

import re

from digsim.verilog import KEYWORDS, TokenKind, tokenize, tokenize_line


# The keywords that open a block, the next line is indented one step more
_OPENERS = {
    "begin",
    "fork",
    "case",
    "casex",
    "casez",
    "module",
    "function",
    "task",
    "generate",
    "interface",
    "package",
    "class",
}
_BRACKETS = {"(": ")", "[": "]", "{": "}"}


def leading(line: str) -> str:
    """The whitespace at the start of a line"""
    return line[: len(line) - len(line.lstrip())]


def indent_lines(lines: list[str], indent: int) -> list[str]:
    """The lines indented one step, empty lines stay empty"""
    return [" " * indent + line if line.strip() else line for line in lines]


def unindent_lines(lines: list[str], indent: int) -> list[str]:
    """The lines moved one step left, as far as they have whitespace"""
    result = []
    for line in lines:
        spaces = len(line) - len(line.lstrip(" \t"))
        result.append(line[min(spaces, indent) :])
    return result


def toggle_comment(lines: list[str]) -> list[str]:
    """
    Comment out the lines with "// ", at the indentation of the least indented line, or
    remove the comments if all lines with text are comments
    """
    texts = [line for line in lines if line.strip()]
    if not texts:
        return lines
    if all(line.lstrip().startswith("//") for line in texts):
        result = []
        for line in lines:
            stripped = line.lstrip()
            if stripped.startswith("//"):
                rest = stripped[2:]
                rest = rest.removeprefix(" ")
                line = leading(line) + rest
            result.append(line)
        return result
    column = min(len(leading(line)) for line in texts)
    return [line[:column] + "// " + line[column:] if line.strip() else line for line in lines]


def new_line_indent(line: str, indent: int) -> str:
    """
    The indentation of a new line after a line (when Enter is pressed at its end): the
    same as the line, one step more after a block keyword or an open bracket
    """
    tokens, _ = tokenize_line(line)
    code = [
        token for token in tokens if token.kind not in (TokenKind.WHITESPACE, TokenKind.COMMENT)
    ]
    whitespace = leading(line)
    if not code:
        return whitespace
    depth = 0
    # A block keyword after the last end keyword on the line ("end else begin")
    opens = False
    for token in code:
        if token.kind == TokenKind.OPERATOR and token.text in _BRACKETS:
            depth += 1
        elif token.kind == TokenKind.OPERATOR and token.text in _BRACKETS.values():
            depth -= 1
        elif token.kind == TokenKind.KEYWORD and token.text in _OPENERS:
            opens = True
        elif token.kind == TokenKind.KEYWORD and token.text.startswith(("end", "join")):
            opens = False
    if depth > 0 or opens:
        return whitespace + " " * indent
    return whitespace


def matching_bracket(text: str, position: int) -> tuple[int, int] | None:
    """
    The bracket at a position (or just before it) and its match, as positions in the
    text. Brackets in comments and strings don't count. None if there is no bracket there
    or it has no match.
    """
    lines = text.split("\n")
    starts = [0]
    for line in lines[:-1]:
        starts.append(starts[-1] + len(line) + 1)
    brackets = [
        (starts[token.line] + token.column, token.text)
        for token in tokenize(text)
        if token.kind == TokenKind.OPERATOR and token.text in "()[]{}"
    ]
    at = {pos: index for index, (pos, _) in enumerate(brackets)}
    index = at.get(position, at.get(position - 1))
    if index is None:
        return None
    start, bracket = brackets[index]
    closers = {close: open_ for open_, close in _BRACKETS.items()}
    if bracket in _BRACKETS:
        step, same, other = 1, bracket, _BRACKETS[bracket]
    else:
        step, same, other = -1, bracket, closers[bracket]
    depth = 0
    for pos, other_bracket in brackets[index::step]:
        if other_bracket == same:
            depth += 1
        elif other_bracket == other:
            depth -= 1
            if depth == 0:
                return start, pos
    return None


def module_name(file_name: str) -> str:
    """
    A Verilog module name from a file name: letters, digits and _, not first a digit, and
    not a keyword (like "and" or "wire")
    """
    stem = file_name.rsplit(".", 1)[0] if "." in file_name else file_name
    name = re.sub(r"[^a-zA-Z0-9_]", "_", stem)
    if not name or name[0].isdigit() or name in KEYWORDS:
        name = "m_" + name
    return name


def new_module_text(name: str) -> str:
    """A new Verilog file with a module of a name: one input and one output"""
    return f"module {name} (\n    input a,\n    output y\n);\n    assign y = a;\nendmodule\n"
