# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""A 7-segment component placed in the GUI"""

from __future__ import annotations

import typing
from typing import TYPE_CHECKING

from PySide6.QtCore import QPoint, QSize, Qt
from PySide6.QtGui import QPainter, QPainterPath

from digsim.circuit.components import HexDigit, SevenSegment
from digsim.circuit.components.atoms import Component

from ._component_object import ComponentObject


if TYPE_CHECKING:
    from digsim.app.model import AppModel


class SevenSegmentObject(ComponentObject):
    """The class for a 7-segment component placed in the GUI"""

    SEGMENT_TYPE_AND_POS: typing.ClassVar[dict[str, tuple[str, QPoint]]] = {
        "A": ("H", QPoint(3, 0)),
        "B": ("V", QPoint(31, 3)),
        "C": ("V", QPoint(31, 33)),
        "D": ("H", QPoint(3, 61)),
        "E": ("V", QPoint(0, 33)),
        "F": ("V", QPoint(0, 3)),
        "G": ("H", QPoint(3, 31)),
    }

    SEGMENT_CORDS: typing.ClassVar[dict[str, list[QPoint]]] = {
        "V": [
            QPoint(3, 3),
            QPoint(3, 20),
            QPoint(0, 25),
            QPoint(-3, 20),
            QPoint(-3, 3),
            QPoint(0, 0),
        ],
        "H": [
            QPoint(3, 3),
            QPoint(20, 3),
            QPoint(25, 0),
            QPoint(20, -3),
            QPoint(3, -3),
            QPoint(0, 0),
        ],
    }

    PORT_TO_RECT_MARGIN = 5
    RECT_TO_DIGIT_RECT_MARGIN = 5
    DIGIT_RECT_TO_DIGIT_MARGIN = 10
    DIGIT_WIDTH = 54
    DIGIT_HEIGHT = 80

    DOT_OFFSET_X = 40
    DOT_OFFSET_Y = 60
    DOT_RADIUS = 3

    def __init__(
        self,
        app_model: AppModel,
        component: Component,
        xpos: float,
        ypos: float,
        port_distance: int = 10,
    ) -> None:
        super().__init__(app_model, component, xpos, ypos, port_distance=port_distance)
        self.setup_size()

    @property
    def component(self) -> SevenSegment | HexDigit:
        component = self._component
        assert isinstance(component, (SevenSegment, HexDigit))
        return component

    def setup_size(self) -> None:
        """Setup the size of the component"""
        str_pixels_w, _ = self.get_string_metrics("dot")
        self.digit_left = self.inport_x_pos() + str_pixels_w + self.PORT_TO_RECT_MARGIN
        self.width = self.digit_left + self.DIGIT_WIDTH + self.RECT_TO_DIGIT_RECT_MARGIN
        self.update_ports()

    def paint_component(self, painter: QPainter) -> None:
        self.paint_component_base(painter)
        digit_ypos = self.height / 2 - self.DIGIT_HEIGHT / 2
        self.paint_digit_rect(
            painter, self.object_pos.x() + self.digit_left, self.object_pos.y() + digit_ypos
        )
        active_segments = self.component.segments()
        self.draw_digit(
            painter,
            self.object_pos.x() + self.digit_left,
            self.object_pos.y() + digit_ypos,
            active_segments,
        )

    @classmethod
    def paint_selectable_component(cls, painter: QPainter, size: QSize, name: str) -> None:
        cls.paint_selectable_digit(painter, size, name, "ADEFG")

    @classmethod
    def paint_selectable_digit(
        cls, painter: QPainter, size: QSize, name: str, segments: str
    ) -> None:
        """Paint a digit (for the component selector)"""
        xpos = size.width() / 2 - cls.DIGIT_WIDTH / 2
        cls.paint_digit_rect(painter, xpos, 0)
        cls.draw_digit(painter, xpos, 0, segments)
        cls.paint_selectable_component_name(painter, QPoint(0, 0), size, name)

    @classmethod
    def paint_digit_rect(
        cls, painter: QPainter, xpos: float, ypos: float, digits: int = 1
    ) -> None:
        """Paint the digit background"""
        painter.setBrush(Qt.BrushStyle.SolidPattern)
        painter.setPen(Qt.GlobalColor.black)
        painter.drawRoundedRect(
            int(xpos), int(ypos), cls.DIGIT_WIDTH * digits, cls.DIGIT_HEIGHT, 4, 4
        )

    @classmethod
    def draw_digit(cls, painter: QPainter, xpos: float, ypos: float, active_segments: str) -> None:
        """Paint the LED digit segments"""
        start_point = QPoint(
            int(xpos + cls.DIGIT_RECT_TO_DIGIT_MARGIN), int(ypos + cls.DIGIT_RECT_TO_DIGIT_MARGIN)
        )
        for seg, type_pos in cls.SEGMENT_TYPE_AND_POS.items():
            if seg in active_segments:
                painter.setPen(Qt.GlobalColor.red)
                painter.setBrush(Qt.GlobalColor.red)
            else:
                painter.setPen(Qt.GlobalColor.darkRed)
                painter.setBrush(Qt.GlobalColor.darkRed)
            pos_vector = cls.SEGMENT_CORDS[type_pos[0]]
            offset = type_pos[1]
            path = QPainterPath()
            path.moveTo(offset + start_point)
            for point in pos_vector:
                path.lineTo(offset + point + start_point)
            path.closeSubpath()
            painter.drawPath(path)

        DOT_OFFSET_X = 40
        DOT_OFFSET_Y = 60
        DOT_RADIUS = 3

        if "." in active_segments:
            painter.setPen(Qt.GlobalColor.red)
            painter.setBrush(Qt.GlobalColor.red)
        else:
            painter.setPen(Qt.GlobalColor.darkRed)
            painter.setBrush(Qt.GlobalColor.darkRed)
        dotPoint = QPoint(DOT_OFFSET_X, DOT_OFFSET_Y) + start_point
        painter.drawEllipse(dotPoint, DOT_RADIUS, DOT_RADIUS)
