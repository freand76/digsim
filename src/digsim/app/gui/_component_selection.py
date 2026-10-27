# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""Module for the component selection classes"""

from __future__ import annotations

from functools import partial

from PySide6.QtCore import QMimeData, QPoint, QSize, Qt, QTimer
from PySide6.QtGui import QDrag, QMouseEvent, QPainter, QPaintEvent, QPixmap
from PySide6.QtWidgets import QApplication, QFrame, QLabel, QPushButton, QVBoxLayout, QWidget

import digsim.app.gui_objects
from digsim.app._component_catalog import COMPONENT_GROUPS

from ._circuit_area import CircuitArea


def start_component_drag(source: QWidget, name: str) -> None:
    """Drag a component (its class name) into the circuit area"""
    drag = QDrag(source)
    mime = QMimeData()
    mime.setText(name)
    drag.setMimeData(mime)
    # No drag image: the circuit area shows a preview of the component where it will
    # be dropped. A drag without an image gets a default one on some platforms.
    pixmap = QPixmap(1, 1)
    pixmap.fill(Qt.GlobalColor.transparent)
    drag.setPixmap(pixmap)
    drag.exec(Qt.DropAction.CopyAction | Qt.DropAction.MoveAction, Qt.DropAction.CopyAction)


class SelectableComponentWidget(QPushButton):
    """
    The selectable component class,
    this is the component widget that can be dragged into the circuit area.
    """

    def __init__(
        self,
        name: str,
        parent: QWidget,
        circuit_area: CircuitArea,
        display_name: str | None = None,
    ) -> None:
        super().__init__(parent)
        self._name = name
        self._circuit_area = circuit_area
        self._paint_class = digsim.app.gui_objects.class_factory(name)
        self._press_pos: QPoint | None = None
        if display_name is not None:
            self._display_name = display_name
        else:
            self._display_name = name

    def sizeHint(self) -> QSize:
        """QT event callback function"""
        return QSize(80, 105)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """QT event callback function"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_pos = event.position().toPoint()

    def mouseReleaseEvent(self, _: QMouseEvent) -> None:
        """QT event callback function"""
        self._press_pos = None

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """QT event callback function"""
        # Start dragging when the mouse has moved a bit with the button pressed, a click
        # (or the first click of a double click) doesn't start a drag
        if self._press_pos is None or not event.buttons() & Qt.MouseButton.LeftButton:
            return
        pos = event.position().toPoint()
        if (pos - self._press_pos).manhattanLength() < QApplication.startDragDistance():
            return
        self._press_pos = None
        start_component_drag(self, self._name)

    def mouseDoubleClickEvent(self, _: QMouseEvent) -> None:
        """QT event callback function"""
        QTimer.singleShot(0, partial(self._circuit_area.add_component, self._name, None))

    def paintEvent(self, _: QPaintEvent) -> None:
        """QT event callback function"""
        painter = QPainter(self)
        self._paint_class.paint_selectable_component(painter, self.size(), self._display_name)


class HorizontalLine(QFrame):
    """
    Horizontal line for the component selection
    """

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.HLine)
        self.setFrameShadow(QFrame.Shadow.Sunken)


class DescriptionText(QWidget):
    """
    Text label for the component selection
    """

    def __init__(self, parent: QWidget, text: str) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        layout.addWidget(HorizontalLine(self))
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        layout.addWidget(HorizontalLine(self))


class ComponentSelection(QWidget):
    """
    The component selection area,
    these are the components that can be dragged into the circuit area.
    """

    def __init__(self, circuit_area: CircuitArea, parent: QWidget) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        for group, entries in COMPONENT_GROUPS:
            layout.addWidget(DescriptionText(self, group))
            for entry in entries:
                layout.addWidget(
                    SelectableComponentWidget(
                        entry.name, self, circuit_area, display_name=entry.display_name
                    )
                )
