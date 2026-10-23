# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""A Logic Analyzer component placed in the GUI"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QPoint, QPointF, QRectF, QSize
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

    SIGNAL_NAME_WIDTH = 40
    ANALYZER_DISPLAY_WIDTH = 200

    _ANALYZER_PEN = QPen(QColor("#4ade80"))
    _SIGNAL_VERTICAL_SCALE = 10
    _SIGNAL_HORIZONTAL_SCALE = 2

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
        theme.paint_window(
            painter,
            QRectF(
                self.object_pos.x() + self.SIGNAL_NAME_WIDTH,
                self.object_pos.y() + self.RECT_TO_BORDER,
                self.ANALYZER_DISPLAY_WIDTH,
                self.height - 2 * self.RECT_TO_BORDER,
            ),
        )

        # A copy: the class pen is shared by all instances
        pen = QPen(self._ANALYZER_PEN)
        pen.setWidth(2)
        painter.setPen(pen)
        signal_data_dict = self.component.signal_data()
        for portname, signal_data in signal_data_dict.items():
            signal_data = signal_data_dict[portname]
            port_pos = self.get_port_pos(portname)
            path = QPainterPath(
                QPoint(
                    int(self.object_pos.x() + self.SIGNAL_NAME_WIDTH),
                    int(port_pos.y() - signal_data[0] * self._SIGNAL_VERTICAL_SCALE),
                )
            )
            last_level = signal_data[0]
            for idx, level in enumerate(signal_data[1:]):
                if level == last_level:
                    continue
                path.lineTo(
                    QPoint(
                        int(
                            self.object_pos.x()
                            + self.SIGNAL_NAME_WIDTH
                            + (idx + 1) * self._SIGNAL_HORIZONTAL_SCALE
                        ),
                        int(port_pos.y() - last_level * self._SIGNAL_VERTICAL_SCALE),
                    )
                )
                path.lineTo(
                    QPoint(
                        int(
                            self.object_pos.x()
                            + self.SIGNAL_NAME_WIDTH
                            + (idx + 1) * self._SIGNAL_HORIZONTAL_SCALE
                        ),
                        int(port_pos.y() - level * self._SIGNAL_VERTICAL_SCALE),
                    )
                )
                last_level = level
            path.lineTo(
                QPoint(
                    int(
                        self.object_pos.x()
                        + self.SIGNAL_NAME_WIDTH
                        + len(signal_data) * self._SIGNAL_HORIZONTAL_SCALE
                    ),
                    int(port_pos.y() - last_level * self._SIGNAL_VERTICAL_SCALE),
                )
            )
            painter.drawPath(path)

    @classmethod
    def paint_selectable_component(cls, painter: QPainter, size: QSize, name: str) -> None:
        def paint(rect: QRectF) -> None:
            theme.paint_body(painter, rect)
            window = rect.adjusted(14, 4, -4, -4)
            theme.paint_window(painter, window)
            pen = QPen(cls._ANALYZER_PEN)
            pen.setWidthF(1.5)
            painter.setPen(pen)
            for row, edges in enumerate(([0.2, 0.5, 0.8], [0.35, 0.65], [0.1, 0.3, 0.6, 0.9])):
                y = window.top() + 12 + 13 * row
                path = QPainterPath(QPointF(window.left() + 2, y))
                level = 0
                for edge in edges:
                    x = window.left() + 2 + edge * (window.width() - 4)
                    path.lineTo(x, y - level * 7)
                    level = 1 - level
                    path.lineTo(x, y - level * 7)
                path.lineTo(window.right() - 2, y - level * 7)
                painter.drawPath(path)
            port_dots(
                painter,
                [QPointF(rect.left() - 1, rect.top() + 12 + 13 * row - 3) for row in range(3)],
            )

        paint_icon(painter, size, (60, 46), paint, scale=1.0)
        cls.paint_selectable_component_name(painter, QPointF(0, 0), size, name)
