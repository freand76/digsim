# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""The component search: find a component by typing, instead of scrolling for it"""

from __future__ import annotations

from collections.abc import Callable
from functools import partial

from PySide6.QtCore import QEvent, QObject, QPoint, QSize, Qt, QTimer
from PySide6.QtGui import QIcon, QKeyEvent, QPainter, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

import digsim.app.gui_objects
from digsim.app._component_catalog import search_components

from ._circuit_area import CircuitArea
from ._component_selection import start_component_drag


# The most results shown without scrolling
MAX_ROWS = 8
ICON_SIZE = 28
# The results are wider than the component selection, over the circuit area
RESULTS_WIDTH = 200
_NAME_ROLE = Qt.ItemDataRole.UserRole

_icons: dict[str, QIcon] = {}


def component_icon(name: str) -> QIcon:
    """The symbol of a component from the component selection, without its name"""
    if name not in _icons:
        size = QSize(80, 105)
        pixmap = QPixmap(size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        digsim.app.gui_objects.class_factory(name).paint_selectable_component(painter, size, "")
        painter.end()
        # The symbol is in the square at the top, the name below it
        _icons[name] = QIcon(pixmap.copy(0, 0, 80, 80))
    return _icons[name]


class _ResultList(QListWidget):
    """The components that match, they can be dragged into the circuit area"""

    def __init__(self, parent: QWidget, dropped: Callable[[], None]) -> None:
        super().__init__(parent)
        self._dropped = dropped
        self.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setTextElideMode(Qt.TextElideMode.ElideRight)

    def startDrag(self, _: Qt.DropAction) -> None:
        """QT function: drag the component, like from the component selection"""
        item = self.currentItem()
        if item is not None:
            start_component_drag(self, item.data(_NAME_ROLE))
            self._dropped()


class ComponentSearch(QWidget):
    """
    A search field, and the components that match what is typed in it, the best first
    (see search_components), in a list over the circuit area ('overlay_parent' is the
    widget it is on). Enter adds the first one (or the selected one), a double click
    adds one, and they can be dragged into the circuit area. Then the search is done.
    Esc clears the search, and it closes when the focus goes elsewhere.
    """

    def __init__(
        self, circuit_area: CircuitArea, parent: QWidget, overlay_parent: QWidget
    ) -> None:
        super().__init__(parent)
        self._circuit_area = circuit_area
        self._overlay_parent = overlay_parent
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        self._field = QLineEdit(self)
        self._field.setPlaceholderText("Search (Ctrl+K)")
        self._field.setClearButtonEnabled(True)
        self._field.textChanged.connect(self._search)
        self._field.returnPressed.connect(self._add_selected)
        self._field.installEventFilter(self)
        layout.addWidget(self._field)
        self._results = _ResultList(overlay_parent, self._clear)
        self._results.itemActivated.connect(self._add_item)
        self._results.installEventFilter(self)
        self._results.setVisible(False)
        app = QApplication.instance()
        if isinstance(app, QApplication):
            app.focusChanged.connect(self._focus_changed)

    def focus_search(self) -> None:
        """Bring the search to the front: the field gets the focus, its text selected"""
        self._field.setFocus(Qt.FocusReason.ShortcutFocusReason)
        self._field.selectAll()

    def _search(self, query: str) -> None:
        self._results.clear()
        for entry in search_components(query):
            item = QListWidgetItem(component_icon(entry.name), entry.display_name)
            item.setData(_NAME_ROLE, entry.name)
            item.setToolTip(f"{entry.display_name}: drag it, or double-click to add it")
            self._results.addItem(item)
        rows = self._results.count()
        if rows > 0:
            self._results.setCurrentRow(0)
        row_height = max(self._results.sizeHintForRow(0), ICON_SIZE + 4) if rows else 20
        height = min(max(rows, 1), MAX_ROWS) * row_height + 2 * self._results.frameWidth()
        # Under the search field, on top of everything
        pos = self._field.mapTo(self._overlay_parent, QPoint(0, self._field.height() + 2))
        self._results.setGeometry(pos.x(), pos.y(), RESULTS_WIDTH, height)
        self._results.setVisible(bool(query.strip()))
        self._results.raise_()

    def _focus_changed(self, _old: QWidget | None, new: QWidget | None) -> None:
        """The results close when the focus leaves the search"""
        if new is not None and new not in (self._field, self._results):
            self._results.setVisible(False)

    def _add_selected(self) -> None:
        """Add the selected component, the best match unless another one was chosen"""
        item = self._results.currentItem()
        if item is not None:
            self._add_item(item)

    def _add_item(self, item: QListWidgetItem) -> None:
        name = item.data(_NAME_ROLE)
        self._clear()
        # Not now: the settings dialog of the component would run inside this event
        QTimer.singleShot(0, partial(self._circuit_area.add_component, name, None))

    def _clear(self) -> None:
        self._field.clear()
        self._circuit_area.setFocus()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """QT function: the arrow keys move in the results, Esc clears the search"""
        if event.type() != QEvent.Type.KeyPress or not isinstance(event, QKeyEvent):
            return super().eventFilter(watched, event)
        key = event.key()
        if key == Qt.Key.Key_Escape:
            self._clear()
            return True
        if watched is self._field and key in (Qt.Key.Key_Down, Qt.Key.Key_Up):
            row = self._results.currentRow() + (1 if key == Qt.Key.Key_Down else -1)
            if 0 <= row < self._results.count():
                self._results.setCurrentRow(row)
            return True
        return super().eventFilter(watched, event)
