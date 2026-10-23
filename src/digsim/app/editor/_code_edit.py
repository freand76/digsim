# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""The text area of the Verilog editor: line numbers, indentation and marks on lines"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import (
    QColor,
    QFontDatabase,
    QKeyEvent,
    QPainter,
    QPaintEvent,
    QResizeEvent,
    QTextCharFormat,
    QTextCursor,
    QTextFormat,
)
from PySide6.QtWidgets import QPlainTextEdit, QTextEdit, QWidget

from digsim.app._editor_text import (
    indent_lines,
    matching_bracket,
    new_line_indent,
    toggle_comment,
    unindent_lines,
)

from ._highlighter import VerilogHighlighter, is_dark


class _LineNumberArea(QWidget):
    """The line numbers to the left of the text"""

    def __init__(self, editor: CodeEdit) -> None:
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self) -> QSize:
        """Qt: the width of the line numbers"""
        return QSize(self._editor.line_number_width(), 0)

    def paintEvent(self, event: QPaintEvent) -> None:
        """Qt: draw the line numbers"""
        self._editor.paint_line_numbers(event)


class CodeEdit(QPlainTextEdit):
    """
    A text area for Verilog: a monospace font, line numbers, syntax highlighting, spaces
    for tabs, the indentation of the line before on a new line, and marks for errors and
    warnings on lines
    """

    def __init__(self, parent: QWidget | None = None, indent: int = 4) -> None:
        super().__init__(parent)
        self.indent = indent
        font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        self.setFont(font)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(" ") * indent)
        self._highlighter = VerilogHighlighter(self.document())
        self._line_numbers = _LineNumberArea(self)
        # Line number (from 1) to (kind, text), see set_marks
        self._marks: dict[int, tuple[str, str]] = {}
        self.blockCountChanged.connect(self._update_margins)
        self.updateRequest.connect(self._update_line_numbers)
        self.cursorPositionChanged.connect(self._update_selections)
        self.textChanged.connect(self._text_changed)
        self._update_margins()
        self._update_selections()

    # Line numbers

    def line_number_width(self) -> int:
        """The width of the line number area"""
        digits = max(3, len(str(self.blockCount())))
        return 10 + self.fontMetrics().horizontalAdvance("9") * digits

    def _update_margins(self) -> None:
        self.setViewportMargins(self.line_number_width(), 0, 0, 0)

    def _update_line_numbers(self, rect: QRect, dy: int) -> None:
        if dy:
            self._line_numbers.scroll(0, dy)
        else:
            self._line_numbers.update(0, rect.y(), self._line_numbers.width(), rect.height())

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Qt: the line numbers follow the height of the text area"""
        super().resizeEvent(event)
        contents = self.contentsRect()
        self._line_numbers.setGeometry(
            QRect(contents.left(), contents.top(), self.line_number_width(), contents.height())
        )

    def paint_line_numbers(self, event: QPaintEvent) -> None:
        """Draw the line numbers, in the colour of a mark on the line"""
        painter = QPainter(self._line_numbers)
        palette = self.palette()
        painter.fillRect(event.rect(), palette.alternateBase())
        block = self.firstVisibleBlock()
        number = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())
        current = self.textCursor().blockNumber()
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                mark = self._marks.get(number + 1)
                if mark is not None:
                    painter.setPen(self._mark_color(mark[0]))
                elif number == current:
                    painter.setPen(palette.text().color())
                else:
                    painter.setPen(palette.placeholderText().color())
                painter.drawText(
                    0,
                    top,
                    self._line_numbers.width() - 5,
                    self.fontMetrics().height(),
                    int(Qt.AlignmentFlag.AlignRight),
                    str(number + 1),
                )
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            number += 1
        painter.end()

    # Selections: the current line, matching brackets and marks

    @staticmethod
    def _mark_color(kind: str) -> QColor:
        return QColor("#e05252") if kind == "error" else QColor("#d89b28")

    def _update_selections(self) -> None:
        selections: list[QTextEdit.ExtraSelection] = []
        current = QTextEdit.ExtraSelection()
        current.format.setBackground(QColor("#32363d") if is_dark() else QColor("#f2f6fc"))
        current.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
        current.cursor = self.textCursor()
        current.cursor.clearSelection()
        selections.append(current)
        for line, (kind, _) in self._marks.items():
            block = self.document().findBlockByNumber(line - 1)
            if not block.isValid():
                continue
            mark = QTextEdit.ExtraSelection()
            mark.format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.WaveUnderline)
            mark.format.setUnderlineColor(self._mark_color(kind))
            mark.cursor = QTextCursor(block)
            mark.cursor.movePosition(
                QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor
            )
            selections.append(mark)
        position = self.textCursor().position()
        document = self.document()
        brackets = None
        # The whole text is tokenized, only when the cursor is at a bracket
        if any(document.characterAt(at) in "()[]{}" for at in (position, position - 1)):
            brackets = matching_bracket(self.toPlainText(), position)
        if brackets is not None:
            for position in brackets:
                bracket = QTextEdit.ExtraSelection()
                bracket.format.setBackground(QColor("#3b514d") if is_dark() else QColor("#b4e3d8"))
                bracket.cursor = self.textCursor()
                bracket.cursor.setPosition(position)
                bracket.cursor.movePosition(
                    QTextCursor.MoveOperation.NextCharacter, QTextCursor.MoveMode.KeepAnchor
                )
                selections.append(bracket)
        self.setExtraSelections(selections)

    def set_marks(self, marks: dict[int, tuple[str, str]]) -> None:
        """
        Mark lines with errors and warnings, until the text changes: line number (from 1)
        to (kind, message), kind "error" or "warning"
        """
        self._marks = dict(marks)
        self._update_selections()
        self._line_numbers.update()

    def marks(self) -> dict[int, tuple[str, str]]:
        """The marked lines, see set_marks"""
        return dict(self._marks)

    def _text_changed(self) -> None:
        if self._marks:
            self._marks = {}
            self._line_numbers.update()
        self._update_selections()

    # Editing

    def go_to_line(self, line: int) -> None:
        """Move the cursor to the start of a line (from 1)"""
        block = self.document().findBlockByNumber(max(0, line - 1))
        if not block.isValid():
            block = self.document().lastBlock()
        cursor = QTextCursor(block)
        self.setTextCursor(cursor)
        self.centerCursor()
        self.setFocus()

    def _selected_blocks(self) -> tuple[int, int]:
        """The first and last line number (from 0) of the selection"""
        cursor = self.textCursor()
        start = self.document().findBlock(cursor.selectionStart()).blockNumber()
        end_position = cursor.selectionEnd()
        end = self.document().findBlock(end_position).blockNumber()
        # A selection that ends at the start of a line doesn't include it
        at_line_start = self.document().findBlock(end_position).position() == end_position
        if cursor.hasSelection() and end > start and at_line_start:
            end -= 1
        return start, end

    def _change_lines(self, change: Callable[[list[str]], list[str]]) -> None:
        """Replace the selected lines with changed ones, as one undo step"""
        start, end = self._selected_blocks()
        document = self.document()
        first = document.findBlockByNumber(start)
        last = document.findBlockByNumber(end)
        lines = [document.findBlockByNumber(n).text() for n in range(start, end + 1)]
        changed = change(lines)
        if changed == lines:
            return
        cursor = QTextCursor(first)
        cursor.setPosition(last.position() + last.length() - 1, QTextCursor.MoveMode.KeepAnchor)
        cursor.beginEditBlock()
        cursor.insertText("\n".join(changed))
        cursor.endEditBlock()
        # Select the changed lines
        cursor.setPosition(document.findBlockByNumber(start).position())
        last = document.findBlockByNumber(end)
        cursor.setPosition(last.position() + last.length() - 1, QTextCursor.MoveMode.KeepAnchor)
        self.setTextCursor(cursor)

    def indent_selection(self) -> None:
        """Indent the selected lines one step"""
        self._change_lines(lambda lines: indent_lines(lines, self.indent))

    def unindent_selection(self) -> None:
        """Move the selected lines one step left"""
        self._change_lines(lambda lines: unindent_lines(lines, self.indent))

    def toggle_comment(self) -> None:
        """Comment out the selected lines, or remove their comments"""
        self._change_lines(toggle_comment)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Qt: Tab indents, Shift+Tab unindents, Enter keeps the indentation"""
        key = event.key()
        cursor = self.textCursor()
        if key == Qt.Key.Key_Tab and not event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            start, end = self._selected_blocks()
            if cursor.hasSelection() and end > start:
                self.indent_selection()
            else:
                column = cursor.positionInBlock()
                cursor.insertText(" " * (self.indent - column % self.indent))
            return
        if key == Qt.Key.Key_Backtab:
            self.unindent_selection()
            return
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not event.modifiers():
            line = cursor.block().text()[: cursor.positionInBlock()]
            cursor.beginEditBlock()
            cursor.insertText("\n" + new_line_indent(line, self.indent))
            cursor.endEditBlock()
            self.ensureCursorVisible()
            return
        super().keyPressEvent(event)
