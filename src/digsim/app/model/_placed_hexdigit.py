# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QPainterPath

from ._placed_component import PlacedComponent


class PlacedHexDigit(PlacedComponent):

    SEGMENT_TYPE_AND_POS = {
        "A": ("H", QPoint(3, 0)),
        "B": ("V", QPoint(31, 3)),
        "C": ("V", QPoint(31, 33)),
        "D": ("H", QPoint(3, 61)),
        "E": ("V", QPoint(0, 33)),
        "F": ("V", QPoint(0, 3)),
        "G": ("H", QPoint(3, 31)),
    }

    SEGMENT_CORDS = {
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
    RECT_TO_DIGIT_MARGIN = 10

    def paint_component(self, painter):
        self.paint_component_base(painter)
        painter.setBrush(Qt.SolidPattern)
        painter.setPen(Qt.black)
        painter.setBrush(Qt.black)
        _, str_pixels_w, _ = self.get_port_display_name_metrics("val")
        first_left = self.inport_x_pos() + str_pixels_w + self.PORT_TO_RECT_MARGIN
        painter.drawRoundedRect(first_left, 10, 57, 80, 4, 4)
        self.draw_digit(painter, QPoint(first_left + self.RECT_TO_DIGIT_MARGIN, 20))

    def draw_digit(self, painter, start_point):
        active_segments = self.component.segments()
        for seg, type_pos in self.SEGMENT_TYPE_AND_POS.items():
            if seg in active_segments:
                painter.setPen(Qt.red)
                painter.setBrush(Qt.red)
            else:
                painter.setPen(Qt.darkRed)
                painter.setBrush(Qt.darkRed)
            pos_vector = self.SEGMENT_CORDS[type_pos[0]]
            offset = type_pos[1]
            path = QPainterPath()
            path.moveTo(offset + start_point)
            for point in pos_vector:
                path.lineTo(offset + point + start_point)
            path.closeSubpath()
            painter.drawPath(path)

        if "." in active_segments:
            painter.setPen(Qt.red)
            painter.setBrush(Qt.red)
        else:
            painter.setPen(Qt.darkRed)
            painter.setBrush(Qt.darkRed)
        dotPoint = QPoint(40, 60) + start_point
        painter.drawEllipse(dotPoint, 3, 3)