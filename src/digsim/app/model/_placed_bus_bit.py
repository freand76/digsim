# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

""" A hexdigit component placed in the GUI """

from PySide6.QtCore import QPoint, QSize, Qt
from PySide6.QtGui import QPen

from ._placed_component import PlacedComponent


# pylint: disable=too-many-arguments


class PlacedBusBits(PlacedComponent):
    """The class for a bus/bit component placed in the GUI"""

    WIRE_LENGTH_COMPONENT = 5
    WIRE_LENGTH_SELECTABLE = 15

    @classmethod
    def _paint_bus_bit(cls, painter, size, border, wire_length, bit_wires_y):
        center_pos = QPoint(size.width() / 2, size.height() / 2)
        center_pos += border
        pen = QPen()
        pen.setWidth(4)
        pen.setColor(Qt.black)
        painter.setPen(pen)
        line_height = size.height() - cls.BORDER_TO_PORT
        painter.drawLine(
            center_pos.x(),
            center_pos.y() - line_height / 2,
            center_pos.x(),
            center_pos.y() + line_height / 2,
        )
        painter.drawLine(
            center_pos.x() - wire_length, center_pos.y(), center_pos.x(), center_pos.y()
        )
        pen.setWidth(2)
        painter.setPen(pen)
        for wire_y in bit_wires_y:
            painter.drawLine(center_pos.x() + wire_length, wire_y, center_pos.x(), wire_y)

    def paint_component(self, painter):
        self.paint_component_base(painter)
        bit_wires_y = []
        for bit in range(self.component.bus.width):
            bit_wires_y.append(self.get_port_pos(f"bus_{bit}").y())
        border = QPoint(self.RECT_TO_BORDER, self.RECT_TO_BORDER)
        self._paint_bus_bit(
            painter, self.get_rect(), border, self.WIRE_LENGTH_COMPONENT, bit_wires_y
        )

    @classmethod
    def paint_selectable_component(cls, painter, size, name):
        image_size = QSize(size.width(), size.width())
        bit_wires_y = [
            size.width() / 2 - 3 * size.width() / 12,
            size.width() / 2 - 1 * size.width() / 12,
            size.width() / 2 + 1 * size.width() / 12,
            size.width() / 2 + 3 * size.width() / 12,
        ]
        border = QPoint(0, 0)
        cls._paint_bus_bit(painter, image_size, border, cls.WIRE_LENGTH_SELECTABLE, bit_wires_y)
        cls.paint_selectable_component_name(painter, size, name)


class PlacedBitsBus(PlacedBusBits):
    """The class for a bit/bit component placed in the GUI"""

    WIRE_LENGTH_COMPONENT = -5
    WIRE_LENGTH_SELECTABLE = -15
