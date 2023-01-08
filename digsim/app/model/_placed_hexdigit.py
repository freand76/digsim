from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QPainterPath

from ._placed_component import PlacedComponent


class PlacedHexDigit(PlacedComponent):

    SEGMENT_TYPE_AND_POS = {
        "A": ("H", QPoint(51, 20)),
        "B": ("V", QPoint(79, 23)),
        "C": ("V", QPoint(79, 53)),
        "D": ("H", QPoint(51, 81)),
        "E": ("V", QPoint(48, 53)),
        "F": ("V", QPoint(48, 23)),
        "G": ("H", QPoint(51, 51)),
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

    def paint_component(self, painter):
        self.paint_component_base(painter)
        painter.setBrush(Qt.SolidPattern)
        painter.setPen(Qt.black)
        painter.setBrush(Qt.black)
        painter.drawRoundedRect(33, 10, 60, 80, 3, 3)

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
            path.moveTo(offset)
            for point in pos_vector:
                path.lineTo(offset + point)
            path.closeSubpath()
            painter.drawPath(path)

        if "." in active_segments:
            painter.setPen(Qt.red)
            painter.setBrush(Qt.red)
        else:
            painter.setPen(Qt.darkRed)
            painter.setBrush(Qt.darkRed)
        painter.drawEllipse(80, 80, 5, 5)
