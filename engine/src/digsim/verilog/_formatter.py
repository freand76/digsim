# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""A Verilog formatter that only changes the indentation and the whitespace around lines"""

from __future__ import annotations

from dataclasses import dataclass

from ._lexer import DIRECTIVES, LexState, Token, TokenKind, split_lines, tokenize, tokenize_line


class VerilogFormatError(ValueError):
    """The formatted text would not have the same tokens, so it is not formatted"""


# The keywords that open a block, and the keywords that close it
_BLOCKS = {
    "begin": ("end",),
    "fork": ("join", "join_any", "join_none"),
    "case": ("endcase",),
    "casex": ("endcase",),
    "casez": ("endcase",),
    "randcase": ("endcase",),
    "module": ("endmodule",),
    "macromodule": ("endmodule",),
    "interface": ("endinterface",),
    "package": ("endpackage",),
    "program": ("endprogram",),
    "class": ("endclass",),
    "function": ("endfunction",),
    "task": ("endtask",),
    "generate": ("endgenerate",),
    "specify": ("endspecify",),
    "primitive": ("endprimitive",),
    "table": ("endtable",),
    "config": ("endconfig",),
    "covergroup": ("endgroup",),
    "property": ("endproperty",),
    "sequence": ("endsequence",),
    "clocking": ("endclocking",),
    "checker": ("endchecker",),
}
_CLOSERS = {closer for closers in _BLOCKS.values() for closer in closers}
# A block keyword after one of these on its line doesn't open a block: "extern function f();",
# "wait fork;", "assert property (...)", "typedef class c;" and "virtual interface i"
_NOT_A_BLOCK_AFTER = {
    "function": {"extern", "pure", "import", "export"},
    "task": {"extern", "pure", "import", "export"},
    "fork": {"wait", "disable"},
    "property": {"assert", "assume", "cover", "restrict", "expect"},
    "sequence": {"assert", "assume", "cover", "restrict", "expect"},
    "class": {"typedef"},
    "interface": {"virtual"},
}
_BRACKETS = {"(": ")", "[": "]", "{": "}"}


@dataclass
class _Open:
    """A block or a bracket that is open, and the indentation of the line it opened on"""

    closers: tuple[str, ...]
    indent: int


def _code(tokens: list[Token]) -> list[Token]:
    return [
        token for token in tokens if token.kind not in (TokenKind.WHITESPACE, TokenKind.COMMENT)
    ]


def _is_directive_line(code: list[Token]) -> bool:
    """A line with a compiler directive like `ifdef or `define, not a macro"""
    return len(code) > 0 and code[0].kind == TokenKind.DIRECTIVE and code[0].text[1:] in DIRECTIVES


def _same_tokens(text: str) -> list[tuple[TokenKind, str]]:
    """The tokens to compare before and after formatting: no whitespace, comment lines stripped"""
    return [
        (token.kind, token.text.strip())
        for token in tokenize(text)
        if token.kind != TokenKind.WHITESPACE
    ]


class VerilogFormatter:
    """
    Formats Verilog and SystemVerilog. Only the whitespace changes: the indentation of
    each line, whitespace at the end of lines, and blank lines.

    - A block (`module`, `begin`, `case`, `function` and so on, to its `end` keyword) and
      a bracket that is open at the end of a line indent the lines in it one step.
    - A line that doesn't end a statement (like `if (a)` or `assign y = a &`) indents
      the next line one step.
    - Tabs at the start of a line become spaces, there is at most `blank_lines` empty
      lines in a row, and the text ends with one newline.

    Comments and strings are not changed, and lines that a `define continues are kept as
    they are. The lines of a block comment move with its first line.

    Args:
        indent: The number of spaces for one step of indentation.
        blank_lines: The most empty lines in a row.
    """

    def __init__(self, indent: int = 4, blank_lines: int = 1) -> None:
        self._indent = indent
        self._blank_lines = blank_lines

    def format(self, text: str) -> str:
        """
        The formatted text. The newlines are the ones of the text (\\n or \\r\\n).

        Raises:
            VerilogFormatError: If formatting would change the tokens of the text. That
                is a bug in the formatter, and the text is not formatted.
        """
        newline = "\r\n" if "\r\n" in text else "\n"
        lines = self._format_lines(split_lines(text))
        formatted = newline.join(lines) + newline if lines else ""
        if _same_tokens(formatted) != _same_tokens(text):
            raise VerilogFormatError("Formatting would change the code, the text is not formatted")
        return formatted

    def _format_lines(self, lines: list[str]) -> list[str]:
        stack: list[_Open] = []
        # The line before doesn't end its statement, the next line is indented a step more
        continued = False
        # How far the lines of a block comment move (in characters)
        comment_shift = 0
        state = LexState.CODE
        result: list[str] = []
        for number, line in enumerate(lines):
            start_state = state
            tokens, state = tokenize_line(line, state, number)
            code = _code(tokens)
            if start_state in (LexState.DEFINE, LexState.STRING):
                # Continued with a backslash: kept as it is
                result.append(line)
                continue
            if start_state == LexState.BLOCK_COMMENT:
                result.append(self._shift(line, comment_shift).rstrip())
                level = self._line_level(stack, code, continued)
            elif line.strip() == "":
                result.append("")
                continue
            else:
                level = self._line_level(stack, code, continued)
                indent = level * self._indent
                result.append(" " * indent + line.strip())
                comment_shift = indent - (len(line) - len(line.lstrip()))
            if code and not _is_directive_line(code):
                continued = self._update(stack, code, level)
        return self._blank(result)

    @staticmethod
    def _shift(line: str, shift: int) -> str:
        """Move a line of a block comment, but not into its text"""
        if shift >= 0:
            return " " * shift + line
        leading = len(line) - len(line.lstrip(" "))
        return line[min(-shift, leading) :]

    @staticmethod
    def _line_level(stack: list[_Open], code: list[Token], continued: bool) -> int:
        """The indentation of a line: a line that starts with a closer is at its opener"""
        if code and not _is_directive_line(code):
            first = code[0].text
            for open_index in range(len(stack) - 1, -1, -1):
                if first in stack[open_index].closers:
                    return stack[open_index].indent
        level = stack[-1].indent + 1 if stack else 0
        return level + 1 if continued else level

    @staticmethod
    def _update(stack: list[_Open], code: list[Token], level: int) -> bool:
        """
        Open and close the blocks and brackets of a line. Returns True if the line doesn't
        end a statement, so that the next line continues it.
        """
        depth = len(stack)
        for index, token in enumerate(code):
            text = token.text
            closes = token.kind == TokenKind.OPERATOR and text in _BRACKETS.values()
            closes = closes or (token.kind == TokenKind.KEYWORD and text in _CLOSERS)
            if closes:
                for open_index in range(len(stack) - 1, -1, -1):
                    if text in stack[open_index].closers:
                        del stack[open_index:]
                        break
                depth = min(depth, len(stack))
            elif token.kind == TokenKind.OPERATOR and text in _BRACKETS:
                stack.append(_Open((_BRACKETS[text],), level))
            elif token.kind == TokenKind.KEYWORD and text in _BLOCKS:
                before = {token.text for token in code[:index]}
                if not before & _NOT_A_BLOCK_AFTER.get(text, set()):
                    stack.append(_Open(_BLOCKS[text], level))
        if len(stack) > depth:
            # A block or bracket is still open from this line
            return False
        if stack and stack[-1].closers[0] in _BRACKETS.values():
            # In a bracket, the lines are indented by the bracket
            return False
        last = code[-1]
        if last.text == ";":
            return False
        if last.kind == TokenKind.KEYWORD and (last.text in _CLOSERS or last.text in _BLOCKS):
            return False
        # A block with a name: "end : name"
        return not (len(code) >= 3 and code[-2].text == ":" and code[-3].text in _CLOSERS)

    def _blank(self, lines: list[str]) -> list[str]:
        """At most blank_lines empty lines in a row, and none at the start and end"""
        result: list[str] = []
        empty = 0
        for line in lines:
            if line == "":
                empty += 1
                continue
            if result:
                result.extend([""] * min(empty, self._blank_lines))
            empty = 0
            result.append(line)
        return result
