# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""The hex editor: the contents of a RAM or ROM, as its file fills it"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QPersistentModelIndex, Qt
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from digsim.app._memory_contents import (
    WORDS_PER_ROW,
    ascii_text,
    parse_word,
    read_contents,
    word_text,
    write_contents,
)
from digsim.app.settings._dialog_flags import DIALOG_FLAGS
from digsim.circuit.components import RAM, ROM
from digsim.circuit.components._memory import _FILEINFO
from digsim.circuit.components.atoms import DigsimException


if TYPE_CHECKING:
    from digsim.app.gui_objects import ComponentObject
    from digsim.app.model import AppModel

Index = QModelIndex | QPersistentModelIndex


class _WordsModel(QAbstractTableModel):
    """
    The words of a memory, a row of WORDS_PER_ROW words and their characters (for a
    memory of bytes). The words before the load address can't be changed, the file
    doesn't have them.
    """

    def __init__(self, words: list[int], data_width: int, load_address: int) -> None:
        super().__init__()
        self.words = words
        self._data_width = data_width
        self._load_address = load_address
        self._ascii = data_width == 8
        self.changed = False

    def rowCount(self, parent: Index | None = None) -> int:
        """QT function"""
        return (len(self.words) + WORDS_PER_ROW - 1) // WORDS_PER_ROW

    def columnCount(self, parent: Index | None = None) -> int:
        """QT function"""
        return WORDS_PER_ROW + (1 if self._ascii else 0)

    def address(self, index: Index) -> int:
        """The address of the word at an index"""
        return index.row() * WORDS_PER_ROW + index.column()

    def _is_word(self, index: Index) -> bool:
        return index.column() < WORDS_PER_ROW and self.address(index) < len(self.words)

    def data(self, index: Index, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """QT function"""
        if not index.isValid():
            return None
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            if index.column() == WORDS_PER_ROW:
                start = index.row() * WORDS_PER_ROW
                return ascii_text(self.words[start : start + WORDS_PER_ROW])
            if self._is_word(index):
                return word_text(self.words[self.address(index)], self._data_width)
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return int(Qt.AlignmentFlag.AlignCenter)
        if role == Qt.ItemDataRole.ToolTipRole and self._is_word(index):
            address = self.address(index)
            if address < self._load_address:
                return f"{address:#x}: before the load address, not in the file"
            return f"{address:#x}"
        return None

    def flags(self, index: Index) -> Qt.ItemFlag:
        """QT function"""
        if not self._is_word(index):
            return Qt.ItemFlag.ItemIsEnabled
        if self.address(index) < self._load_address:
            return Qt.ItemFlag.NoItemFlags
        return (
            Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable
        )

    def setData(self, index: Index, value: Any, role: int = Qt.ItemDataRole.EditRole) -> bool:
        """QT function: a word typed in hexadecimal"""
        if role != Qt.ItemDataRole.EditRole or not self._is_word(index):
            return False
        try:
            word = parse_word(str(value), self._data_width)
        except ValueError:
            return False
        address = self.address(index)
        if self.words[address] != word:
            self.words[address] = word
            self.changed = True
            self.dataChanged.emit(index, index)
            if self._ascii:
                text = self.index(index.row(), WORDS_PER_ROW)
                self.dataChanged.emit(text, text)
        return True

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole
    ) -> Any:
        """QT function: the address of each row, and the last digit of each column"""
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Vertical:
            digits = max(1, (len(self.words) - 1).bit_length() + 3) // 4
            return f"{section * WORDS_PER_ROW:0{digits}X}"
        return "ASCII" if section == WORDS_PER_ROW else f"{section:X}"


class HexEditorDialog(QDialog):
    """
    The hex editor of a RAM or ROM: the words its file fills it with, from the load
    address. Save writes them in the file, in its format (text or binary), and the memory
    reads it again: the simulation starts over. A RAM without a file asks for one.
    """

    def __init__(
        self, parent: QWidget | None, app_model: AppModel, component_object: ComponentObject
    ) -> None:
        super().__init__(parent)
        self.setWindowFlags(DIALOG_FLAGS)
        self._app_model = app_model
        self._object = component_object
        memory = self._memory
        self._path: str | None = memory.parameter_get("path")
        self._data_width: int = memory.parameter_get("data_width")
        self._load_address: int = memory.parameter_get("load_address")
        words = read_contents(
            self._path,
            memory.parameter_get("address_width"),
            self._data_width,
            self._load_address,
        )
        self.setWindowTitle(f"Contents of {memory.name()}")
        layout = QVBoxLayout(self)
        self._file_label = QLabel(self)
        self._file_label.setWordWrap(True)
        layout.addWidget(self._file_label)
        self._show_file()

        self.model = _WordsModel(words, self._data_width, self._load_address)
        self.table = QTableView(self)
        self.table.setModel(self.model)
        self.table.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setFont(self.table.font())
        self.table.resizeColumnsToContents()
        layout.addWidget(self.table, 1)

        row = QHBoxLayout()
        row.addWidget(QLabel("Go to address:", self))
        self._goto = QLineEdit(self)
        self._goto.setPlaceholderText("Hexadecimal, like 1F0")
        self._goto.returnPressed.connect(self._go_to)
        self._goto.setMinimumWidth(180)
        row.addWidget(self._goto)
        row.addStretch(1)
        layout.addLayout(row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Close, self
        )
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        width = self.table.verticalHeader().width() + header.length() + 40
        self.resize(max(width, 360), 480)

    @property
    def _memory(self) -> RAM | ROM:
        component = self._object.component
        assert isinstance(component, (RAM, ROM))
        return component

    def _show_file(self) -> None:
        if self._path:
            where = f" at {self._load_address:#x}" if self._load_address else ""
            self._file_label.setText(f"From {self._path}{where}")
        else:
            self._file_label.setText("No file, the RAM starts with zeros. Save asks for one.")

    def _go_to(self) -> None:
        """Show the row of an address and select its word"""
        try:
            address = parse_word(self._goto.text(), 32)
        except ValueError:
            return
        if address >= len(self.model.words):
            return
        index = self.model.index(address // WORDS_PER_ROW, address % WORDS_PER_ROW)
        self.table.scrollTo(index, QTableView.ScrollHint.PositionAtCenter)
        self.table.setCurrentIndex(index)

    def _ask_path(self) -> str:
        """A file for a RAM that has none, "" if that was cancelled"""
        path, _ = QFileDialog.getSaveFileName(self, "Save the contents", "", _FILEINFO)
        return path

    def save(self) -> bool:
        """Save the words in the file, and let the memory read it. False if it wasn't."""
        path = self._path or self._ask_path()
        if not path:
            return False
        try:
            write_contents(path, self.model.words, self._data_width, self._load_address)
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Save the contents", f"Could not save {path}: {exc}")
            return False
        components = self._app_model.objects.components
        if self._path is None:
            # A new file for the RAM, it is built again with it (an undo step)
            name = self._memory.name()
            if not components.change_settings(self._object, {"path": str(Path(path))}):
                return False
            self._object = next(
                obj for comp, obj in components.get_dict().items() if comp.name() == name
            )
        else:
            try:
                self._memory.reload_contents()
            except DigsimException as exc:
                QMessageBox.critical(self, "Save the contents", str(exc))
                return False
            self._app_model.model_init()
        self._path = path
        self._show_file()
        self.model.changed = False
        self._app_model.sig_repaint.emit()
        return True

    def reject(self) -> None:
        """QT function: Close, asking first when there are changes that aren't saved"""
        if self.model.changed:
            answer = QMessageBox.question(
                self,
                "Close the hex editor",
                "The contents have changed. Save them?",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save,
            )
            if answer == QMessageBox.StandardButton.Cancel:
                return
            if answer == QMessageBox.StandardButton.Save and not self.save():
                return
        super().reject()
