# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

""" A label component placed in the GUI """

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QPen, QPolygon

from ._component_object import ComponentObject


class LabelObject(ComponentObject):
    """The class for a bus/bit component placed in the GUI"""

    def __init__(self, app_model, component, xpos, ypos):
        super().__init__(app_model, component, xpos, ypos)
        label = component.label()
        _, label_w, label_h = self.get_port_display_name_metrics(label)
        self._width = 2 * self.RECT_TO_BORDER + 2 * self.PORT_SIDE + label_w
        self._height = 2 * self.RECT_TO_BORDER + self.PORT_SIDE + label_h
        self._input = len(self._component.inports()) > 0

        if self._input:
            xpos = 0
        else:
            xpos = self._width - self.PORT_SIDE - 1

        self._port_rects[label] = QRect(
            self.pos.x() + xpos,
            self.pos.y() + self._height / 2 - self.PORT_SIDE / 2,
            self.PORT_SIDE,
            self.PORT_SIDE,
        )

    @classmethod
    def _paint_label(cls, painter, comp_rect, name, selected=False):
        pen = QPen()
        if selected:
            pen.setWidth(4)
        else:
            pen.setWidth(1)
        pen.setColor(Qt.black)
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
        comp_rect = self.get_rect()
        if self._input:
            self._paint_label(painter, comp_rect, "sink", self.selected)
        else:
            self._paint_label(painter, comp_rect, "source", self.selected)

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