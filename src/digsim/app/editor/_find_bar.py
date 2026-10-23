# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""Find and replace in the Verilog editor"""

from __future__ import annotations

from PySide6.QtGui import QKeySequence, QShortcut, QTextCursor, QTextDocument
from PySide6.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QWidget,
)


class FindBar(QWidget):
    """A bar below the text: find, and replace when it is opened for that"""

    def __init__(self, editor: QPlainTextEdit, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._editor = editor
        layout = QGridLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        self._status = QLabel(self)
        self._find = QLineEdit(self)
        self._find.setPlaceholderText("Find")
        self._find.returnPressed.connect(self.find_next)
        self._find.textChanged.connect(lambda: self._status.setText(""))
        self._replace = QLineEdit(self)
        self._replace.setPlaceholderText("Replace with")
        self._replace.returnPressed.connect(self.replace)
        self._case = QCheckBox("Match case", self)
        self._words = QCheckBox("Whole words", self)
        next_button = QPushButton("Next", self)
        next_button.clicked.connect(self.find_next)
        previous_button = QPushButton("Previous", self)
        previous_button.clicked.connect(self.find_previous)
        self._replace_button = QPushButton("Replace", self)
        self._replace_button.clicked.connect(self.replace)
        self._replace_all_button = QPushButton("Replace all", self)
        self._replace_all_button.clicked.connect(self.replace_all)
        close_button = QPushButton("Close", self)
        close_button.clicked.connect(self.close_bar)
        layout.addWidget(self._find, 0, 0)
        layout.addWidget(next_button, 0, 1)
        layout.addWidget(previous_button, 0, 2)
        layout.addWidget(self._case, 0, 3)
        layout.addWidget(self._words, 0, 4)
        layout.addWidget(close_button, 0, 5)
        layout.addWidget(self._replace, 1, 0)
        layout.addWidget(self._replace_button, 1, 1)
        layout.addWidget(self._replace_all_button, 1, 2)
        layout.addWidget(self._status, 1, 3, 1, 3)
        layout.setColumnStretch(0, 1)
        QShortcut(QKeySequence("Escape"), self, self.close_bar)
        self.hide()

    def open_bar(self, replace: bool = False) -> None:
        """Show the bar, with the selected text to find"""
        selected = self._editor.textCursor().selectedText()
        if selected and " " not in selected:
            self._find.setText(selected)
        for widget in (self._replace, self._replace_button, self._replace_all_button):
            widget.setVisible(replace)
        self._status.setText("")
        self.show()
        self._find.setFocus()
        self._find.selectAll()

    def close_bar(self) -> None:
        """Hide the bar, and go back to the text"""
        self.hide()
        self._editor.setFocus()

    def set_text(self, find: str, replace: str = "") -> None:
        """Set the text to find and to replace it with"""
        self._find.setText(find)
        self._replace.setText(replace)

    def _flags(self, backward: bool = False) -> QTextDocument.FindFlag:
        flags = QTextDocument.FindFlag(0)
        if self._case.isChecked():
            flags |= QTextDocument.FindFlag.FindCaseSensitively
        if self._words.isChecked():
            flags |= QTextDocument.FindFlag.FindWholeWords
        if backward:
            flags |= QTextDocument.FindFlag.FindBackward
        return flags

    def _find_text(self, backward: bool) -> bool:
        text = self._find.text()
        if not text:
            return False
        if self._editor.find(text, self._flags(backward)):
            self._status.setText("")
            return True
        # From the other end of the text
        cursor = self._editor.textCursor()
        cursor.movePosition(
            QTextCursor.MoveOperation.End if backward else QTextCursor.MoveOperation.Start
        )
        self._editor.setTextCursor(cursor)
        if self._editor.find(text, self._flags(backward)):
            self._status.setText("Wrapped around")
            return True
        self._status.setText("Not found")
        return False

    def find_next(self) -> bool:
        """Select the next match, True if there is one"""
        return self._find_text(backward=False)

    def find_previous(self) -> bool:
        """Select the match before, True if there is one"""
        return self._find_text(backward=True)

    def _is_match(self, selected: str) -> bool:
        text = self._find.text()
        if self._case.isChecked():
            return selected == text
        return selected.lower() == text.lower()

    def replace(self) -> None:
        """Replace the selected match, and select the next one"""
        cursor = self._editor.textCursor()
        if cursor.hasSelection() and self._is_match(cursor.selectedText()):
            cursor.insertText(self._replace.text())
        self.find_next()

    def replace_all(self) -> int:
        """Replace all matches, as one undo step. Returns the number of matches."""
        text = self._find.text()
        if not text:
            return 0
        document = self._editor.document()
        cursor = QTextCursor(document)
        cursor.beginEditBlock()
        count = 0
        found = document.find(text, cursor, self._flags())
        while not found.isNull():
            found.insertText(self._replace.text())
            count += 1
            found = document.find(text, found, self._flags())
        cursor.endEditBlock()
        self._status.setText(f"Replaced {count}")
        return count
