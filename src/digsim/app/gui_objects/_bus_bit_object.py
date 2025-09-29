# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""A hexdigit component placed in the GUI"""

from PySide6.QtCore import QPoint, QSize, Qt
from PySide6.QtGui import QPen

from ._component_object import ComponentObject


class BusBitsObject(ComponentObject):
    """The class for a bus/bit component placed in the GUI"""

    WIRE_LENGTH_COMPONENT = 5
    WIRE_LENGTH_SELECTABLE = 15
    PORT_DISTANCE = 10

    def __init__(self, app_model, component, xpos, ypos):
        super().__init__(app_model, component, xpos, ypos, port_distance=self.PORT_DISTANCE)
        bus_w, _ = self.get_string_metrics("bus[31:0]")
        self.width = 2 * self.inport_x_pos() + 2 * bus_w + abs(2 * self.WIRE_LENGTH_COMPONENT)
        self.update_ports()

    @classmethod
    def _paint_bus_bit(cls, painter, pos, size, wire_length, bit_wires_y):
        center_pos = QPoint(size.width() / 2, size.height() / 2)
        pen = QPen()
        pen.setWidth(4)
        pen.setColor(Qt.black)
        painter.setPen(pen)
        line_height = size.height() - cls.BORDER_TO_PORT
        painter.drawLine(
            pos.x() + center_pos.x(),
            pos.y() + center_pos.y() - line_height / 2,
            pos.x() + center_pos.x(),
            pos.y() + center_pos.y() + line_height / 2,
        )
        painter.drawLine(
            pos.x() + center_pos.x() - wire_length,
            pos.y() + center_pos.y(),
            pos.x() + center_pos.x(),
            pos.y() + center_pos.y(),
        )
        pen.setWidth(2)
        painter.setPen(pen)
        for wire_y in bit_wires_y:
            painter.drawLine(
                pos.x() + center_pos.x() + wire_length, wire_y, pos.x() + center_pos.x(), wire_y
            )

    def _portlist(self):
        return self.component.outports()

    def paint_component(self, painter):
        self.paint_component_base(painter)
        bit_wires_y = []
        for port in self._portlist():
            bit_wires_y.append(self.get_port_pos(port.name()).y())
        self._paint_bus_bit(
            painter,
            self.object_pos,
            self.rect(),
            self.WIRE_LENGTH_COMPONENT,
            bit_wires_y,
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
        cls._paint_bus_bit(
            painter,
            QPoint(0, 0),
            image_size,
            cls.WIRE_LENGTH_SELECTABLE,
            bit_wires_y,
        )
        cls.paint_selectable_component_name(painter, QPoint(0, 0), size, name)


class BitsBusObject(BusBitsObject):
    """The class for a bit/bit component placed in the GUI"""

    WIRE_LENGTH_COMPONENT = -5
    WIRE_LENGTH_SELECTABLE = -15

    def _portlist(self):
        return self.component.inports()
