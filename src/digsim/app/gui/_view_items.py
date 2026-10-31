# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""The items of the read-only views: their ports, and their lines with the values of the wires"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QGraphicsItem, QStyleOptionGraphicsItem, QWidget

from digsim.app._value_text import value_text
from digsim.app.gui_objects import _theme as theme
from digsim.app.gui_objects._circuit_port_object import (
    CircuitInOutObject,
    CircuitInputObject,
    CircuitOutputObject,
)
from digsim.circuit.components import CircuitPort
from digsim.circuit.components.atoms import VALUE_TYPE, Component, Port, PortInOut


def port_value(port: Port) -> VALUE_TYPE:
    """The value on a port's wire: what an inout port reads, the value of other ports"""
    if isinstance(port, PortInOut):
        return port.read_value()
    return port.value


class OuterPortValue:
    """
    A circuit port drawn in a view, with the value of the port of the subcircuit or
    Verilog component that it is a port of
    """

    outer: Port
    _component: Component

    def _texts(self) -> tuple[str, str]:
        port = self._component
        assert isinstance(port, CircuitPort)
        return port.label(), value_text(port_value(self.outer), port.width)


class ViewInput(OuterPortValue, CircuitInputObject):
    """An In, with the value that drives the input"""


class ViewOutput(OuterPortValue, CircuitOutputObject):
    """An Out, with the value of the output"""


class ViewInOut(OuterPortValue, CircuitInOutObject):
    """An InOut, with the value of the wire of the inout port"""


class LinesItem(QGraphicsItem):
    """
    The lines of the subcircuit's file, each with the value of its wire: the value a
    port on it reads, colored like the wires of the circuit area
    """

    def __init__(
        self, lines: list[tuple[list[tuple[QPointF, QPointF]], list[QPointF], Port | None]]
    ) -> None:
        super().__init__()
        # For each line: its segments, its dots, and the port whose value it has
        self._lines = lines
        rect = QRectF()
        for segments, _, _ in lines:
            for start, end in segments:
                rect = rect.united(QRectF(start, end).normalized())
        self._rect = rect.adjusted(-6, -6, 6, 6)
        self.setZValue(-1)
        self.setAcceptedMouseButtons(Qt.MouseButton.NoButton)

    def boundingRect(self) -> QRectF:
        """QT function"""
        return self._rect

    @staticmethod
    def _color(value: VALUE_TYPE, width: int) -> QColor:
        if value == "X":
            return QColor(theme.WIRE_X)
        if value == "Z":
            return QColor(theme.WIRE_Z)
        if not isinstance(value, int) or value == 0:
            return QColor(theme.WIRE)
        return theme.dim(theme.ON, 0.4 + 0.6 * value / (2**width - 1), theme.WIRE)

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        """QT function"""
        for segments, dots, port in self._lines:
            width = port.width if port is not None else 1
            color = self._color(port_value(port) if port is not None else "Z", width)
            pen = QPen(color, 4 if width > 1 else 2)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
            painter.setPen(pen)
            for start, end in segments:
                painter.drawLine(start, end)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            for dot in dots:
                painter.drawEllipse(dot, 4 if width > 1 else 3, 4 if width > 1 else 3)
