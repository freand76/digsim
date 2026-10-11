# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Module for the component selection classes"""

from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING

from PySide6.QtCore import QMimeData, QPoint, QSize, Qt, QTimer
from PySide6.QtGui import QDrag, QMouseEvent, QPainter, QPaintEvent, QPixmap
from PySide6.QtWidgets import QApplication, QFrame, QLabel, QPushButton, QVBoxLayout, QWidget

import digsim.app.gui_objects

from ._circuit_area import CircuitArea


if TYPE_CHECKING:
    from digsim.app.model import AppModel


class SelectableComponentWidget(QPushButton):
    """
    The selectable component class,
    this is the component widget than can be dragged into the circuit area.
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
        hot_spot = self._press_pos
        self._press_pos = None
        drag = QDrag(self)
        mime = QMimeData()
        mime.setText(self._name)
        drag.setMimeData(mime)
        # A transparent image of the whole widget, sharp on high-DPI screens
        ratio = self.devicePixelRatioF()
        pixmap = QPixmap(self.size() * ratio)
        pixmap.setDevicePixelRatio(ratio)
        pixmap.fill(Qt.GlobalColor.transparent)
        self.render(pixmap)
        drag.setPixmap(pixmap)
        drag.setHotSpot(hot_spot)
        drag.exec_(Qt.DropAction.CopyAction | Qt.DropAction.MoveAction, Qt.DropAction.CopyAction)

    def mouseDoubleClickEvent(self, _: QMouseEvent) -> None:
        """QT event callback function"""
        QTimer.singleShot(0, partial(self._circuit_area.add_component, self._name, None))

    def paintEvent(self, event: QPaintEvent) -> None:
        """QT event callback function"""
        if self._paint_class is None:
            super().paintEvent(event)
        else:
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
    these are the components than can be dragged into the circuit area.
    """

    def __init__(self, app_model: AppModel, circuit_area: CircuitArea, parent: QWidget) -> None:
        super().__init__(parent)
        self.app_model = app_model
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        layout.addWidget(DescriptionText(self, "Input"))
        layout.addWidget(SelectableComponentWidget("PushButton", self, circuit_area))
        layout.addWidget(SelectableComponentWidget("OnOffSwitch", self, circuit_area))
        layout.addWidget(
            SelectableComponentWidget("DipSwitch", self, circuit_area, display_name="DIP switch")
        )
        layout.addWidget(SelectableComponentWidget("Clock", self, circuit_area))
        layout.addWidget(SelectableComponentWidget("StaticValue", self, circuit_area))
        layout.addWidget(DescriptionText(self, "Output"))
        layout.addWidget(SelectableComponentWidget("Led", self, circuit_area))
        layout.addWidget(
            SelectableComponentWidget("LedBar", self, circuit_area, display_name="LED bar")
        )
        layout.addWidget(
            SelectableComponentWidget("HexDigit", self, circuit_area, display_name="Hex-digit")
        )
        layout.addWidget(
            SelectableComponentWidget("SevenSegment", self, circuit_area, display_name="7-Seg")
        )
        layout.addWidget(SelectableComponentWidget("Buzzer", self, circuit_area))
        layout.addWidget(
            SelectableComponentWidget(
                "LogicAnalyzer", self, circuit_area, display_name="Logic Analyzer"
            )
        )
        layout.addWidget(DescriptionText(self, "Gates"))
        layout.addWidget(SelectableComponentWidget("OR", self, circuit_area))
        layout.addWidget(SelectableComponentWidget("AND", self, circuit_area))
        layout.addWidget(SelectableComponentWidget("NOT", self, circuit_area))
        layout.addWidget(SelectableComponentWidget("XOR", self, circuit_area))
        layout.addWidget(SelectableComponentWidget("XNOR", self, circuit_area))
        layout.addWidget(SelectableComponentWidget("NAND", self, circuit_area))
        layout.addWidget(SelectableComponentWidget("NOR", self, circuit_area))
        layout.addWidget(SelectableComponentWidget("DFF", self, circuit_area))
        layout.addWidget(SelectableComponentWidget("FlipFlop", self, circuit_area))
        layout.addWidget(SelectableComponentWidget("MUX", self, circuit_area))
        layout.addWidget(DescriptionText(self, "Bus / Wires"))
        layout.addWidget(
            SelectableComponentWidget("LabelWireIn", self, circuit_area, display_name="Wire Sink")
        )
        layout.addWidget(
            SelectableComponentWidget(
                "LabelWireOut", self, circuit_area, display_name="Wire Source"
            )
        )
        layout.addWidget(SelectableComponentWidget("Bus2Wires", self, circuit_area))
        layout.addWidget(SelectableComponentWidget("Wires2Bus", self, circuit_area))
        layout.addWidget(DescriptionText(self, "IC / Verilog"))
        layout.addWidget(
            SelectableComponentWidget("IntegratedCircuit", self, circuit_area, display_name="IC")
        )
        layout.addWidget(
            SelectableComponentWidget("YosysComponent", self, circuit_area, display_name="Yosys")
        )
        layout.addWidget(DescriptionText(self, "Other"))
        layout.addWidget(SelectableComponentWidget("Note", self, circuit_area))
