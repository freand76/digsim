# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""A label component placed in the GUI"""

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QPen, QPolygon

from ._component_object import ComponentObject


class LabelObject(ComponentObject):
    """The class for a bus/bit component placed in the GUI"""

    _LABEL_PEN = QPen(Qt.black)

    def __init__(self, app_model, component, xpos, ypos):
        super().__init__(app_model, component, xpos, ypos)
        label = component.label()
        label_w, label_h = self.get_string_metrics(label)
        self.width = 2 * self.PORT_SIDE + label_w
        self.height = self.PORT_SIDE + label_h
        self._input = len(self._component.inports()) > 0

        if self._input:
            xpos = -ComponentObject.RECT_TO_BORDER
        else:
            xpos = self.width - self.PORT_SIDE - 1
        rect = QRect(
            self.object_pos.x() + xpos,
            self.object_pos.y() + self.height / 2 - self.PORT_SIDE / 2,
            self.PORT_SIDE,
            self.PORT_SIDE,
        )
        port = self.component.port(label)
        self.set_port_rect(port, rect)

    @classmethod
    def _paint_label(cls, painter, comp_rect, name, selected=False):
        pen = cls._LABEL_PEN
        if selected:
            pen.setWidth(4)
        else:
            pen.setWidth(1)
        painter.setPen(pen)
        painter.setBrush(Qt.SolidPattern)
        painter.setBrush(Qt.gray)

        if "in" in name.lower():
            points = QPolygon(
                [
                    QPoint(comp_rect.x(), comp_rect.y() + comp_rect.height() / 2),
                    QPoint(comp_rect.x() + comp_rect.height() / 2, comp_rect.y()),
                    QPoint(comp_rect.x() + comp_rect.width(), comp_rect.y()),
                    QPoint(comp_rect.x() + comp_rect.width(), comp_rect.y() + comp_rect.height()),
                    QPoint(
                        comp_rect.x() + comp_rect.height() / 2, comp_rect.y() + comp_rect.height()
                    ),
                    QPoint(comp_rect.x(), comp_rect.y() + comp_rect.height() / 2),
                ]
            )
        else:
            points = QPolygon(
                [
                    QPoint(comp_rect.x(), comp_rect.y()),
                    QPoint(
                        comp_rect.x() + comp_rect.width() - comp_rect.height() / 2, comp_rect.y()
                    ),
                    QPoint(
                        comp_rect.x() + comp_rect.width(), comp_rect.y() + comp_rect.height() / 2
                    ),
                    QPoint(
                        comp_rect.x() + comp_rect.width() - comp_rect.height() / 2,
                        comp_rect.y() + comp_rect.height(),
                    ),
                    QPoint(comp_rect.x(), comp_rect.y() + comp_rect.height()),
                    QPoint(comp_rect.x(), comp_rect.y()),
                ]
            )
        painter.drawPolygon(points)

    def paint_component(self, painter):
        if self._input:
            self._paint_label(painter, self.rect(), "sink", self.selected)
        else:
            self._paint_label(painter, self.rect(), "source", self.selected)

    @classmethod
    def paint_selectable_component(cls, painter, size, name):
        width = 40
        height = 15
        cls._paint_label(
            painter,
            QRect(size.width() / 2 - width / 2, size.height() / 2 - height / 2, width, height),
            name,
        )
        cls.paint_selectable_component_name(painter, QPoint(0, 0), size, name)
