# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""
The faces of the tokens of a Verilog line for syntax highlighting, like the faces of
Emacs verilog-mode. No Qt, so that it can be tested.
"""

from __future__ import annotations

from enum import StrEnum

from digsim.verilog import Token, TokenKind


class Face(StrEnum):
    """How a token is highlighted (the Emacs font-lock face in the comment)"""

    KEYWORD = "keyword"  # font-lock-keyword-face
    TYPE = "type"  # font-lock-type-face: declarations, types, "@" and "#" delays
    NAME = "name"  # font-lock-function-name-face: the name of a module, function or task
    COMMENT = "comment"  # font-lock-comment-face
    STRING = "string"  # font-lock-string-face
    BUILTIN = "builtin"  # font-lock-builtin-face: system tasks like $display
    DIRECTIVE = "directive"  # font-lock-preprocessor-face: `define, `ifdef and macros
    CONSTANT = "constant"  # font-lock-constant-face: numbers and block labels


def _words(text: str) -> list[str]:
    return text.split()


# The keywords that declare something, or are a type
DECLARATIONS = frozenset(
    _words(
        """
    input output inout ref wire reg logic bit byte shortint int longint integer real
    shortreal realtime time string chandle event tri tri0 tri1 triand trior trireg wand wor
    uwire supply0 supply1 var signed unsigned parameter localparam defparam specparam
    genvar enum struct union packed void const static automatic
    """
    )
)
# The keywords that a name follows
_NAMED_BY = frozenset(
    _words(
        "module macromodule function task interface package program class primitive checker config"
    )
)
# The keywords whose block can have a label: "begin : name"
_LABELED = frozenset(
    _words(
        "begin end fork join join_any join_none endmodule endfunction endtask endcase "
        "endgenerate endinterface endpackage endprogram endclass"
    )
)


def faces(tokens: list[Token]) -> list[tuple[Token, Face]]:
    """The tokens of a line (see tokenize_line) that are highlighted, with their faces"""
    result: list[tuple[Token, Face]] = []
    code = [token for token in tokens if token.kind != TokenKind.WHITESPACE]
    # The keyword that the next identifier is the name of
    naming = False
    for index, token in enumerate(code):
        kind = token.kind
        face: Face | None = None
        if kind == TokenKind.COMMENT:
            face = Face.COMMENT
        elif kind == TokenKind.STRING:
            face = Face.STRING
        elif kind == TokenKind.SYSTEM:
            face = Face.BUILTIN
        elif kind == TokenKind.DIRECTIVE:
            face = Face.DIRECTIVE
        elif kind == TokenKind.NUMBER:
            # A delay ("#10") is like its "#"
            after_hash = index > 0 and code[index - 1].text == "#"
            face = Face.TYPE if after_hash else Face.CONSTANT
        elif kind == TokenKind.KEYWORD:
            face = Face.TYPE if token.text in DECLARATIONS else Face.KEYWORD
            if token.text in _NAMED_BY:
                naming = True
        elif kind == TokenKind.IDENTIFIER:
            if naming:
                face = Face.NAME
                naming = False
            elif (
                index >= 2
                and code[index - 1].text == ":"
                and code[index - 2].kind == TokenKind.KEYWORD
                and code[index - 2].text in _LABELED
            ):
                face = Face.CONSTANT
        elif kind == TokenKind.OPERATOR and token.text in ("@", "#"):
            # Event controls and delays, as verilog-mode
            face = Face.TYPE
        elif kind == TokenKind.OPERATOR and token.text in (";", "("):
            # "module m;": no name after the keyword any more
            naming = False
        if face is not None:
            result.append((token, face))
    return result
