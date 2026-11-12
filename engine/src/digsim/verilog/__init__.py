# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""
Verilog tools: a lexer and a formatter. They only use the Python standard library, and
nothing else of digsim, so they can become a package of their own.
"""

from ._formatter import VerilogFormatError, VerilogFormatter
from ._lexer import (
    DIRECTIVES,
    KEYWORDS,
    LexState,
    Token,
    TokenKind,
    split_lines,
    tokenize,
    tokenize_line,
)
