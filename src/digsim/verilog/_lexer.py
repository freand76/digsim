# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""
A lexer for Verilog and SystemVerilog, for formatting and syntax highlighting.
It works one line at a time, so that a highlighter can lex a changed line again.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum, StrEnum


class TokenKind(StrEnum):
    """The kind of a token"""

    KEYWORD = "keyword"
    IDENTIFIER = "identifier"
    NUMBER = "number"
    STRING = "string"
    COMMENT = "comment"
    DIRECTIVE = "directive"
    SYSTEM = "system"
    OPERATOR = "operator"
    WHITESPACE = "whitespace"


class LexState(Enum):
    """What the next line starts in"""

    CODE = 0
    BLOCK_COMMENT = 1
    # A `define, or a string, continued with a backslash at the end of the line
    DEFINE = 2
    STRING = 3


@dataclass(frozen=True)
class Token:
    """
    A token of a line.

    Args:
        kind: The kind of token.
        text: The text of the token.
        line: The line number, from 0.
        column: The column in the line, from 0.
    """

    kind: TokenKind
    text: str
    line: int
    column: int


def _words(text: str) -> list[str]:
    return text.split()


KEYWORDS = frozenset(
    _words(
        """
    accept_on alias always always_comb always_ff always_latch and assert assign assume
    automatic before begin bind bins binsof bit break buf bufif0 bufif1 byte case casex casez
    cell chandle checker class clocking cmos config const constraint context continue cover
    covergroup coverpoint cross deassign default defparam design disable dist do edge else end
    endcase endchecker endclass endclocking endconfig endfunction endgenerate endgroup
    endinterface endmodule endpackage endprimitive endprogram endproperty endspecify
    endsequence endtable endtask enum event eventually expect export extends extern final
    first_match for force foreach forever fork forkjoin function generate genvar global
    highz0 highz1 if iff ifnone ignore_bins illegal_bins implements implies import incdir
    include initial inout input inside instance int integer interconnect interface intersect
    join join_any join_none large let liblist library local localparam logic longint
    macromodule matches medium modport module nand negedge nettype new nexttime nmos nor
    noshowcancelled not notif0 notif1 null or output package packed parameter pmos posedge
    primitive priority program property protected pull0 pull1 pulldown pullup
    pulsestyle_ondetect pulsestyle_onevent pure rand randc randcase randsequence rcmos real
    realtime ref reg reject_on release repeat restrict return rnmos rpmos rtran rtranif0
    rtranif1 s_always s_eventually s_nexttime s_until s_until_with scalared sequence shortint
    shortreal showcancelled signed small soft solve specify specparam static string strong
    strong0 strong1 struct super supply0 supply1 sync_accept_on sync_reject_on table tagged
    task this throughout time timeprecision timeunit tran tranif0 tranif1 tri tri0 tri1 triand
    trior trireg type typedef union unique unique0 unsigned until until_with untyped use uwire
    var vectored virtual void wait wait_order wand weak weak0 weak1 while wildcard wire with
    within wor xnor xor
    """
    )
)

# The compiler directives that are not macros. A `define takes the rest of the line, and
# the lines after it that a backslash continues.
DIRECTIVES = frozenset(
    _words(
        """
    begin_keywords celldefine default_nettype define else elsif end_keywords endcelldefine
    endif ifdef ifndef include line nounconnected_drive pragma resetall timescale
    unconnected_drive undef undefineall
    """
    )
)

_SIZE = r"(?:\d[\d_]*[ \t]*)?"
_BASED = _SIZE + r"'[sS]?(?:[bB][01xXzZ?_]+|[oO][0-7xXzZ?_]+|[dD][\d_]+|[dD][xXzZ?]_*"
_BASED += r"|[hH][0-9a-fA-FxXzZ?_]+)"
_BASED_SPACED = _SIZE + r"'[sS]?[bBoOdDhH][ \t]+[0-9a-fA-FxXzZ?][0-9a-fA-FxXzZ?_]*"
_REAL = r"\d[\d_]*(?:\.\d[\d_]*)?(?:[eE][+-]?\d[\d_]*)?(?:(?:[fpnum]?s|step)(?![\w$]))?"
_OPERATORS = sorted(
    _words(
        """
    <<<= >>>= <<< >>> === !== ==? !=? <-> ->> |-> |=> <<= >>= ** == != <= >= && || << >> ~& ~|
    ~^ ^~ -> +: -: :: ++ -- += -= *= /= %= &= |= ^= :/ := #- #= ##
    """
    ),
    key=len,
    reverse=True,
)
_TOKEN = re.compile(
    "|".join(
        [
            # Any whitespace, also Unicode like a non-breaking space (a line has no newline)
            r"(?P<whitespace>\s+)",
            r"(?P<line_comment>//.*)",
            r"(?P<block_comment>/\*)",
            r'(?P<string>")',
            r"(?P<directive>`[a-zA-Z_][\w$]*)",
            r"(?P<system>\$[a-zA-Z_][\w$]*)",
            f"(?P<number>{_BASED_SPACED}|{_BASED}|'[01xXzZ](?![\\w$])|{_REAL})",
            r"(?P<identifier>[a-zA-Z_][\w$]*|\\\S+)",
            # Any other character is a token of its own, so that every line is tokenized
            "(?P<operator>" + "|".join(re.escape(op) for op in _OPERATORS) + r"|.)",
        ]
    )
)
_STRING_END = re.compile(r'(?:[^"\\]|\\.)*"')


def tokenize_line(
    text: str, state: LexState = LexState.CODE, line: int = 0
) -> tuple[list[Token], LexState]:
    """
    The tokens of one line (without its newline), and the state the next line starts in.

    Args:
        text: The line.
        state: The state the line starts in, from the line before it.
        line: The line number for the tokens.
    """
    tokens: list[Token] = []
    pos = 0

    def add(kind: TokenKind, end: int) -> None:
        nonlocal pos
        tokens.append(Token(kind, text[pos:end], line, pos))
        pos = end

    if state == LexState.BLOCK_COMMENT:
        end = text.find("*/")
        if end < 0:
            add(TokenKind.COMMENT, len(text))
            return tokens, LexState.BLOCK_COMMENT
        add(TokenKind.COMMENT, end + 2)
    elif state == LexState.DEFINE:
        add(TokenKind.DIRECTIVE, len(text))
        return tokens, LexState.DEFINE if text.endswith("\\") else LexState.CODE
    elif state == LexState.STRING:
        match = _STRING_END.match(text)
        if match is None:
            add(TokenKind.STRING, len(text))
            return tokens, LexState.STRING if text.endswith("\\") else LexState.CODE
        add(TokenKind.STRING, match.end())

    while pos < len(text):
        match = _TOKEN.match(text, pos)
        assert match is not None and match.lastgroup is not None
        group = match.lastgroup
        if group == "block_comment":
            end = text.find("*/", pos + 2)
            if end < 0:
                add(TokenKind.COMMENT, len(text))
                return tokens, LexState.BLOCK_COMMENT
            add(TokenKind.COMMENT, end + 2)
        elif group == "line_comment":
            add(TokenKind.COMMENT, len(text))
        elif group == "string":
            string_end = _STRING_END.match(text, pos + 1)
            if string_end is None:
                # Not closed on this line: continued with a backslash, or a syntax error
                add(TokenKind.STRING, len(text))
                return tokens, LexState.STRING if text.endswith("\\") else LexState.CODE
            add(TokenKind.STRING, string_end.end())
        elif group == "directive" and match.group() == "`define":
            add(TokenKind.DIRECTIVE, len(text))
            return tokens, LexState.DEFINE if text.endswith("\\") else LexState.CODE
        elif group == "identifier" and match.group() in KEYWORDS:
            add(TokenKind.KEYWORD, match.end())
        else:
            add(TokenKind(group), match.end())
    return tokens, LexState.CODE


def split_lines(text: str) -> list[str]:
    """The lines of a text, without their newlines (\\n, \\r\\n or \\r)"""
    return text.replace("\r\n", "\n").replace("\r", "\n").split("\n")


def tokenize(text: str) -> list[Token]:
    """
    The tokens of a Verilog text, line by line. A block comment over several lines is a
    comment token on each line. The newlines are not tokens.
    """
    tokens: list[Token] = []
    state = LexState.CODE
    for number, line in enumerate(split_lines(text)):
        line_tokens, state = tokenize_line(line, state, number)
        tokens.extend(line_tokens)
    return tokens
