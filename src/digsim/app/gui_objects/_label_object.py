# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""A label component placed in the GUI"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QPoint, QRect, QRectF, QSize, Qt
from PySide6.QtGui import QPainter, QPen, QPolygon

from digsim.circuit.components import LabelWireIn, LabelWireOut
from digsim.circuit.components.atoms import Component

from ._component_object import ComponentObject


if TYPE_CHECKING:
    from digsim.app.model import AppModel


class LabelObject(ComponentObject):
    """The class for a label wire component (Wire Sink or Wire Source) placed in the GUI"""

    _LABEL_PEN = QPen(Qt.GlobalColor.black)

    def __init__(
        self, app_model: AppModel, component: Component, xpos: float, ypos: float
    ) -> None:
        super().__init__(app_model, component, xpos, ypos)
        label = self.component.label()
        label_w, label_h = self.get_string_metrics(label)
        self.width = 2 * self.PORT_SIDE + label_w
        self.height = self.PORT_SIDE + label_h
        self._input = len(self._component.inports()) > 0

        if self._input:
            xpos = -ComponentObject.RECT_TO_BORDER
        else:
            xpos = self.width - self.PORT_SIDE - 1
        rect = QRect(
            int(self.object_pos.x() + xpos),
            int(self.object_pos.y() + self.height / 2 - self.PORT_SIDE / 2),
            self.PORT_SIDE,
            self.PORT_SIDE,
        )
        port = self.component.port(label)
        self.set_port_rect(port, rect)

    @property
    def component(self) -> LabelWireIn | LabelWireOut:
        component = self._component
        assert isinstance(component, (LabelWireIn, LabelWireOut))
        return component

    @classmethod
    def _paint_label(
        cls, painter: QPainter, comp_rect: QRect | QRectF, name: str, selected: bool = False
    ) -> None:
        # A copy: the class pen is shared by all instances
        pen = QPen(cls._LABEL_PEN)
        if selected:
            pen.setWidth(4)
        else:
            pen.setWidth(1)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.SolidPattern)
        painter.setBrush(Qt.GlobalColor.gray)

        if "in" in name.lower():
            points = QPolygon(
                [
                    QPoint(int(comp_rect.x()), int(comp_rect.y() + comp_rect.height() / 2)),
                    QPoint(int(comp_rect.x() + comp_rect.height() / 2), int(comp_rect.y())),
                    QPoint(int(comp_rect.x() + comp_rect.width()), int(comp_rect.y())),
                    QPoint(
                        int(comp_rect.x() + comp_rect.width()),
                        int(comp_rect.y() + comp_rect.height()),
                    ),
                    QPoint(
                        int(comp_rect.x() + comp_rect.height() / 2),
                        int(comp_rect.y() + comp_rect.height()),
                    ),
                    QPoint(int(comp_rect.x()), int(comp_rect.y() + comp_rect.height() / 2)),
                ]
            )
        else:
            points = QPolygon(
                [
                    QPoint(int(comp_rect.x()), int(comp_rect.y())),
                    QPoint(
                        int(comp_rect.x() + comp_rect.width() - comp_rect.height() / 2),
                        int(comp_rect.y()),
                    ),
                    QPoint(
                        int(comp_rect.x() + comp_rect.width()),
                        int(comp_rect.y() + comp_rect.height() / 2),
                    ),
                    QPoint(
                        int(comp_rect.x() + comp_rect.width() - comp_rect.height() / 2),
                        int(comp_rect.y() + comp_rect.height()),
                    ),
                    QPoint(int(comp_rect.x()), int(comp_rect.y() + comp_rect.height())),
                    QPoint(int(comp_rect.x()), int(comp_rect.y())),
                ]
            )
        painter.drawPolygon(points)

    def paint_component(self, painter: QPainter) -> None:
        if self._input:
            self._paint_label(painter, self.rect(), "sink", self.selected)
        else:
            self._paint_label(painter, self.rect(), "source", self.selected)

    @classmethod
    def paint_selectable_component(cls, painter: QPainter, size: QSize, name: str) -> None:
        width = 40
        height = 15
        cls._paint_label(
            painter,
            QRect(
                int(size.width() / 2 - width / 2),
                int(size.height() / 2 - height / 2),
                width,
                height,
            ),
            name,
        )
        cls.paint_selectable_component_name(painter, QPoint(0, 0), size, name)
