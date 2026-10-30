# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""The hex editor: the contents of a RAM or ROM, as its file fills it"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QPersistentModelIndex, Qt
from PySide6.QtGui import QColor, QFontDatabase, QPainter, QPalette
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from digsim.app._memory_contents import (
    WORDS_PER_ROW,
    ascii_text,
    defined_words,
    has_ascii,
    parse_word,
    read_contents,
    word_text,
    write_contents,
)
from digsim.app.gui_objects import _theme as theme
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
        self._ascii = has_ascii(data_width)
        self.changed = False

    def values(self) -> Sequence[int | str]:
        """The words that are shown"""
        return self.words

    def rowCount(self, parent: Index | None = None) -> int:
        """QT function"""
        return (len(self.values()) + WORDS_PER_ROW - 1) // WORDS_PER_ROW

    def columnCount(self, parent: Index | None = None) -> int:
        """QT function"""
        return WORDS_PER_ROW + (1 if self._ascii else 0)

    def address(self, index: Index) -> int:
        """The address of the word at an index"""
        return index.row() * WORDS_PER_ROW + index.column()

    def _is_word(self, index: Index) -> bool:
        return index.column() < WORDS_PER_ROW and self.address(index) < len(self.values())

    def data(self, index: Index, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """QT function"""
        if not index.isValid():
            return None
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            values = self.values()
            if index.column() == WORDS_PER_ROW:
                start = index.row() * WORDS_PER_ROW
                return ascii_text(list(values[start : start + WORDS_PER_ROW]), self._data_width)
            if self._is_word(index):
                return word_text(values[self.address(index)], self._data_width)
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


class _SimulationWordsModel(_WordsModel):
    """
    The words a RAM has now, in the simulation, read-only: the ones that are not what the
    file fills it with are marked
    """

    def __init__(
        self, now: list[int | str], file_words: list[int], data_width: int, load_address: int
    ) -> None:
        super().__init__(file_words, data_width, load_address)
        self.now = now

    def values(self) -> Sequence[int | str]:
        return self.now

    def is_changed(self, address: int) -> bool:
        """Is a word not what the file fills the RAM with"""
        return self.now[address] != self.words[address]

    def data(self, index: Index, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """QT function"""
        if role == Qt.ItemDataRole.BackgroundRole and self._is_word(index):
            if self.is_changed(self.address(index)):
                # See-through, for the light and the dark theme
                color = QColor(theme.ACCENT)
                color.setAlpha(80)
                return color
            return None
        if role == Qt.ItemDataRole.ToolTipRole and self._is_word(index):
            address = self.address(index)
            if self.is_changed(address):
                file_word = word_text(self.words[address], self._data_width)
                return f"{address:#x}: written by the simulation, the file has {file_word}"
            return f"{address:#x}"
        return super().data(index, role)

    def flags(self, index: Index) -> Qt.ItemFlag:
        """QT function: read-only"""
        if not self._is_word(index):
            return Qt.ItemFlag.ItemIsEnabled
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def setData(self, index: Index, value: Any, role: int = Qt.ItemDataRole.EditRole) -> bool:
        """QT function: read-only"""
        return False


class _TextDelegate(QStyledItemDelegate):
    """
    The text of a row, with the characters of the current word highlighted: one, two or
    four for a word of 8, 16 or 32 bits
    """

    def __init__(self, table: QTableView, data_width: int) -> None:
        super().__init__(table)
        self._table = table
        self._bytes = data_width // 8

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: Index) -> None:
        """QT function: the cell without its text, then the text with the highlight"""
        text = str(index.data())
        cell = QStyleOptionViewItem(option)
        self.initStyleOption(cell, index)
        cell.text = ""
        style = cell.widget.style() if cell.widget is not None else self._table.style()
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, cell, painter, cell.widget)
        metrics = cell.fontMetrics
        rect = cell.rect
        left = rect.left() + (rect.width() - metrics.horizontalAdvance(text)) / 2
        painter.save()
        painter.setFont(cell.font)
        painter.setPen(cell.palette.color(QPalette.ColorRole.Text))
        painter.drawText(rect, int(Qt.AlignmentFlag.AlignCenter), text)
        current = self._table.currentIndex()
        if current.isValid() and current.row() == index.row() and current.column() < WORDS_PER_ROW:
            start = current.column() * self._bytes
            chars = text[start : start + self._bytes]
            if chars:
                mark = rect.adjusted(0, 1, 0, -1)
                mark.setLeft(int(left + metrics.horizontalAdvance(text[:start])))
                mark.setWidth(metrics.horizontalAdvance(chars))
                painter.fillRect(mark, cell.palette.color(QPalette.ColorRole.Highlight))
                painter.setPen(cell.palette.color(QPalette.ColorRole.HighlightedText))
                painter.drawText(mark, int(Qt.AlignmentFlag.AlignCenter), chars)
        painter.restore()


class HexEditorDialog(QDialog):
    """
    The hex editor of a RAM or ROM: the words its file fills it with, from the load
    address. Save writes them in the file, in its format (text or binary), and the memory
    reads it again: the simulation starts over. A RAM without a file asks for one.

    A RAM also shows the words it has now, in the simulation (it is stopped while the
    editor is open), read-only, with the words it wrote marked: Save As... saves them in
    a file of their own, Use as Contents puts them in the file view, to save.
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
        self.now_model: _SimulationWordsModel | None = None
        self._view = QComboBox(self)
        self._view.addItem("Contents of the file")
        if isinstance(memory, RAM):
            time_s = self._app_model.objects.circuit.time_ns / 1e9
            self._view.addItem(f"The RAM now, in the simulation at {time_s:.6g} s")
            self.now_model = _SimulationWordsModel(
                [memory.read(address) for address in range(len(words))],
                words,
                self._data_width,
                self._load_address,
            )
            layout.addWidget(self._view)
        else:
            # A ROM has only its file, the view is not in the layout: not shown in a corner
            self._view.hide()
        self._view.currentIndexChanged.connect(self._show_view)
        self.table = QTableView(self)
        self.table.setModel(self.model)
        self.table.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        if has_ascii(self._data_width):
            self.table.setItemDelegateForColumn(
                WORDS_PER_ROW, _TextDelegate(self.table, self._data_width)
            )
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
        self._save_button = buttons.button(QDialogButtonBox.StandardButton.Save)
        self._dump_button = buttons.addButton("Save As...", QDialogButtonBox.ButtonRole.ActionRole)
        self._dump_button.setToolTip("Save the words the RAM has now in a file")
        self._dump_button.clicked.connect(self.save_simulation_as)
        self._use_button = buttons.addButton(
            "Use as Contents", QDialogButtonBox.ButtonRole.ActionRole
        )
        self._use_button.setToolTip("Put the words the RAM has now in the file view, to save")
        self._use_button.clicked.connect(self.use_simulation)
        layout.addWidget(buttons)
        self._show_view(0)
        width = self.table.verticalHeader().width() + header.length() + 40
        # Wide words, with their text, can be wider than the screen: it scrolls then
        width = min(width, self.screen().availableGeometry().width())
        self.resize(max(width, 360), 480)

    def _show_view(self, view: int) -> None:
        """The file (0, editable) or the RAM in the simulation (1, read-only)"""
        simulation = view == 1 and self.now_model is not None
        self.table.setModel(self.now_model if simulation else self.model)
        # The text of the row shows which characters the current word is
        self.table.selectionModel().currentChanged.connect(lambda: self.table.viewport().update())
        self._save_button.setVisible(not simulation)
        self._dump_button.setVisible(simulation)
        self._use_button.setVisible(simulation)

    def _simulation_words(self) -> list[int]:
        """The words of the RAM now, an undefined one ("X") as 0, with a note if any is"""
        assert self.now_model is not None
        words, undefined = defined_words(self.now_model.now)
        if undefined:
            QMessageBox.information(
                self,
                "The RAM now",
                f"{undefined} words are undefined (X) in the simulation, they are 0 here",
            )
        return words

    def save_simulation_as(self) -> bool:
        """Save As...: the words of the RAM now, in a file of their own (from address 0)"""
        path, _ = QFileDialog.getSaveFileName(self, "Save the RAM as it is now", "", _FILEINFO)
        if not path:
            return False
        words = self._simulation_words()
        try:
            write_contents(path, words, self._data_width, 0)
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Save the RAM", f"Could not save {path}: {exc}")
            return False
        return True

    def use_simulation(self) -> None:
        """Use as Contents: the words of the RAM now, in the file view (from the load
        address, the file has no words before it), to save"""
        words = self._simulation_words()
        for address in range(self._load_address, len(words)):
            self.model.words[address] = words[address]
        self.model.changed = True
        self.model.layoutChanged.emit()
        self._view.setCurrentIndex(0)

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
            component_object = components.change_settings(self._object, {"path": str(Path(path))})
            if component_object is None:
                return False
            self._object = component_object
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
