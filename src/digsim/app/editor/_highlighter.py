# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""Syntax highlighting of Verilog, with the colors of Emacs verilog-mode"""

from __future__ import annotations

from PySide6.QtGui import (
    QColor,
    QFont,
    QPalette,
    QSyntaxHighlighter,
    QTextCharFormat,
    QTextDocument,
)
from PySide6.QtWidgets import QApplication

from digsim.app._verilog_faces import Face, faces
from digsim.verilog import LexState, tokenize_line


# The colors of the Emacs faces, (light background, dark background)
_COLORS = {
    Face.KEYWORD: ("#a020f0", "#00ffff"),  # Purple, Cyan1
    Face.TYPE: ("#228b22", "#98fb98"),  # ForestGreen, PaleGreen
    Face.NAME: ("#0000ff", "#87cefa"),  # Blue1, LightSkyBlue
    Face.COMMENT: ("#b22222", "#ff7f24"),  # Firebrick, chocolate1
    Face.STRING: ("#8b2252", "#ffa07a"),  # VioletRed4, LightSalmon
    Face.BUILTIN: ("#483d8b", "#b0c4de"),  # dark slate blue, LightSteelBlue
    Face.DIRECTIVE: ("#483d8b", "#b0c4de"),  # as builtin, like font-lock-preprocessor-face
    Face.CONSTANT: ("#008b8b", "#7fffd4"),  # dark cyan, Aquamarine
}


def is_dark() -> bool:
    """True if the application has a dark palette"""
    window = QApplication.palette().color(QPalette.ColorRole.Window)
    return window.lightness() < 128


class VerilogHighlighter(QSyntaxHighlighter):
    """Colors the tokens of Verilog, a block comment over lines too"""

    def __init__(self, document: QTextDocument) -> None:
        super().__init__(document)
        dark = int(is_dark())
        self._formats: dict[Face, QTextCharFormat] = {}
        for face, colors in _COLORS.items():
            text_format = QTextCharFormat()
            text_format.setForeground(QColor(colors[dark]))
            if face == Face.NAME:
                text_format.setFontWeight(QFont.Weight.Bold)
            self._formats[face] = text_format

    def highlightBlock(self, text: str) -> None:
        """Qt: color one line, it starts in the state the line before ended in"""
        previous = self.previousBlockState()
        state = LexState(previous) if previous >= 0 else LexState.CODE
        tokens, state = tokenize_line(text, state)
        for token, face in faces(tokens):
            self.setFormat(token.column, len(token.text), self._formats[face])
        self.setCurrentBlockState(state.value)
