# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""A Logic Analyzer component placed in the GUI"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen

from digsim.circuit.components import LogicAnalyzer
from digsim.circuit.components.atoms import Component

from . import _theme as theme
from ._component_object import ComponentObject
from ._symbol_objects import paint_icon, port_dots


if TYPE_CHECKING:
    from digsim.app.model import AppModel


class LogicAnalyzerObject(ComponentObject):
    """The class for a LogicAnalyzer component placed in the GUI"""

    # Room in the window for the traces of the first and the last input
    BORDER_TO_PORT = 20
    SIGNAL_NAME_WIDTH = 40
    ANALYZER_DISPLAY_WIDTH = 200

    _ANALYZER_PEN = QPen(QColor("#4ade80"))
    # From 0 to 1, around the line of the port
    _SIGNAL_HEIGHT = 8
    # From the window to the traces
    _TRACE_INSET = 3

    def __init__(
        self, app_model: AppModel, component: Component, xpos: float, ypos: float
    ) -> None:
        super().__init__(app_model, component, xpos, ypos)
        self.width = self.SIGNAL_NAME_WIDTH + self.ANALYZER_DISPLAY_WIDTH + 2 * self.RECT_TO_BORDER
        self.update_ports()

    @property
    def component(self) -> LogicAnalyzer:
        component = self._component
        assert isinstance(component, LogicAnalyzer)
        return component

    def paint_component(self, painter: QPainter) -> None:
        self.paint_component_base(painter)
        window = QRectF(
            self.object_pos.x() + self.SIGNAL_NAME_WIDTH,
            self.object_pos.y() + self.RECT_TO_BORDER,
            self.ANALYZER_DISPLAY_WIDTH,
            self.height - 2 * self.RECT_TO_BORDER,
        )
        theme.paint_window(painter, window, theme.SCREEN)
        # A copy: the class pen is shared by all instances
        pen = QPen(self._ANALYZER_PEN)
        pen.setWidth(2)
        painter.save()
        painter.setClipRect(window)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        left = window.left() + self._TRACE_INSET
        width = window.width() - 2 * self._TRACE_INSET
        for portname, signal_data in self.component.signal_data().items():
            # 0 below the line of the port, 1 above it
            port_y = self.get_port_pos(portname).y()

            def level_y(level: int, port_y: float = port_y) -> float:
                return port_y + self._SIGNAL_HEIGHT / 2 - level * self._SIGNAL_HEIGHT

            step = width / len(signal_data)
            path = QPainterPath(QPointF(left, level_y(signal_data[0])))
            last_level = signal_data[0]
            for idx, level in enumerate(signal_data[1:], start=1):
                if level != last_level:
                    path.lineTo(left + idx * step, level_y(last_level))
                    path.lineTo(left + idx * step, level_y(level))
                    last_level = level
            path.lineTo(left + width, level_y(last_level))
            painter.drawPath(path)
        painter.restore()

    @classmethod
    def paint_selectable_component(cls, painter: QPainter, size: QSize, name: str) -> None:
        def paint(rect: QRectF) -> None:
            theme.paint_body(painter, rect)
            window = rect.adjusted(14, 4, -4, -4)
            theme.paint_window(painter, window, theme.SCREEN)
            pen = QPen(cls._ANALYZER_PEN)
            pen.setWidthF(1.5)
            painter.save()
            painter.setClipRect(window)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            ys = [window.top() + 9 + 10 * row for row in range(3)]
            for y, edges in zip(
                ys, ([0.2, 0.5, 0.8], [0.35, 0.65], [0.1, 0.3, 0.6, 0.9]), strict=True
            ):
                # 0 below the line, 1 above it, like in the circuit
                low, high = y + 3, y - 3
                path = QPainterPath(QPointF(window.left() + 3, low))
                level_y = low
                for edge in edges:
                    x = window.left() + 3 + edge * (window.width() - 6)
                    path.lineTo(x, level_y)
                    level_y = high if level_y == low else low
                    path.lineTo(x, level_y)
                path.lineTo(window.right() - 3, level_y)
                painter.drawPath(path)
            painter.restore()
            port_dots(painter, [QPointF(rect.left() - 1, y) for y in ys])

        paint_icon(painter, size, (60, 42), paint, scale=1.0)
        cls.paint_selectable_component_name(painter, QPointF(0, 0), size, name)
