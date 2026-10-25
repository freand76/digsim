# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""The parameters of a Verilog module, for each Yosys component of its file"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from digsim.app._yosys_interface import parameter_column
from digsim.app.settings._dialog_flags import DIALOG_FLAGS


class ParametersDialog(QDialog):
    """
    A table of the parameters of a module: a row for each parameter, with its default,
    and a column for each component with its values. An empty value is the default.
    """

    def __init__(
        self,
        parent: QWidget | None,
        module: str,
        defaults: dict[str, int | str],
        components: dict[str, dict[str, int]],
        note: str = "",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Parameters of {module}")
        # Only a close button: a dialog is not minimized or maximized
        self.setWindowFlags(DIALOG_FLAGS)
        self._defaults = defaults
        self._names = list(components)
        layout = QVBoxLayout(self)
        text = "The values of each component, an empty value is the default."
        if note:
            text += f"\n{note}"
        layout.addWidget(QLabel(text))

        self.table = QTableWidget(len(defaults), 2 + len(components), self)
        self.table.setHorizontalHeaderLabels(["Parameter", "Default", *components])
        self.table.verticalHeader().setVisible(False)
        # Edited where the cursor is, a selected cell would only be colored
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        for row, (name, default) in enumerate(defaults.items()):
            for column, label in enumerate((name, str(default))):
                item = QTableWidgetItem(label)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, column, item)
            for column, values in enumerate(components.values(), start=2):
                value = values.get(name)
                item = QTableWidgetItem("" if value is None else str(value))
                item.setToolTip(f"{name} of {self._names[column - 2]}, empty for {default}")
                self.table.setItem(row, column, item)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        # The values share the width that is left
        header.setMinimumSectionSize(70)
        for column in range(2, self.table.columnCount()):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Stretch)
        self.table.itemChanged.connect(self._clear_mark)
        self.table.setCurrentCell(0, 2)
        layout.addWidget(self.table)

        self.error = QLabel("")
        self.error.setStyleSheet("color: red")
        self.error.hide()
        layout.addWidget(self.error)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Reset
        )
        self.synthesize_button = buttons.addButton(
            "Synthesize", QDialogButtonBox.ButtonRole.AcceptRole
        )
        buttons.button(QDialogButtonBox.StandardButton.Reset).setText("All defaults")
        buttons.button(QDialogButtonBox.StandardButton.Reset).clicked.connect(self.clear)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        # High enough for the rows, up to 12 of them (then it scrolls)
        rows = sum(self.table.rowHeight(row) for row in range(min(len(defaults), 12)))
        height = header.height() + rows + 2 * self.table.frameWidth()
        self.table.setMinimumHeight(height)
        if len(defaults) <= 12:
            self.table.setMaximumHeight(height)
        self.resize(max(header.length() + 40, 420), self.sizeHint().height())

    def _item(self, row: int, column: int) -> QTableWidgetItem:
        item = self.table.item(row, column)
        assert item is not None
        return item

    def _texts(self, column: int) -> dict[str, str]:
        return {name: self._item(row, column).text() for row, name in enumerate(self._defaults)}

    def _clear_mark(self, item: QTableWidgetItem) -> None:
        item.setBackground(QBrush())

    def clear(self) -> None:
        """Every value is the default"""
        for row in range(self.table.rowCount()):
            for column in range(2, self.table.columnCount()):
                self._item(row, column).setText("")

    def values(self) -> dict[str, str]:
        """
        The parameters of each component, by name, as "NAME=VALUE,..."

        Raises:
            ValueError: If a value is not an integer, the message says which.
        """
        values = {}
        for column, name in enumerate(self._names, start=2):
            try:
                values[name] = parameter_column(self._texts(column))
            except ValueError as exc:
                row = list(self._defaults).index(exc.args[1])
                # Not itemChanged, which takes the mark away again when the value is edited
                blocked = self.table.blockSignals(True)
                self._item(row, column).setBackground(QColor(255, 200, 200))
                self.table.blockSignals(blocked)
                raise ValueError(f"{name}: {exc.args[0]}") from None
        return values

    def accept(self) -> None:
        try:
            self.values()
        except ValueError as exc:
            self.error.setText(str(exc))
            self.error.show()
            return
        super().accept()
