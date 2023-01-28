# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

""" A wire placed in the GUI """

import math

from PySide6.QtCore import Qt
from PySide6.QtGui import QPen

from digsim.circuit.components.atoms import PortConnectionError

from ._placed_object import PlacedObject


class PlacedWire(PlacedObject):
    """The class for wire placed in the GUI"""

    WIRE_CLICK_CLOSE_PIXELS = 10

    def __init__(self, app_model, port_a, port_b=None, connect=True):
        super().__init__()
        self._app_model = app_model
        self._src_port = None
        self._dst_port = None
        self._connected = False
        self._is_bus = False

        if port_a is None:
            raise PortConnectionError("Cannot start a wire without a port")

        if port_b is not None:
            if port_a.is_output() and port_b.is_input():
                self._src_port = port_a
                self._dst_port = port_b
            elif port_a.is_input() and port_b.is_output():
                self._src_port = port_b
                self._dst_port = port_a
            else:
                raise PortConnectionError("Cannot connect to power of same type")
        else:
            if port_a.is_output():
                self._src_port = port_a
            else:
                self._dst_port = port_a

        self._src_point = None
        self._dst_point = None
        self.update()
        if connect:
            self._connect()

    def _paint_wire(self, painter, src, dst):
        pen = QPen()
        pen.setColor(Qt.darkGray)
        if self.selected:
            pen.setWidth(6)
            pen.setColor(Qt.black)
        elif self._is_bus:
            pen.setWidth(4)
        else:
            pen.setWidth(2)
        painter.setPen(pen)
        painter.drawLine(src, dst)

    def paint(self, painter):
        self._paint_wire(painter, self._src_point, self._dst_point)

    def paint_new(self, painter, end_pos):
        self._paint_wire(painter, self.start_pos, end_pos)

    def _connect(self):
        if self._src_port is not None and self._dst_port is not None:
            self._src_port.wire = self._dst_port
            self._connected = True

    def disconnect(self):
        self._src_port.disconnect(self._dst_port)

    def set_end_port(self, port):
        if port.is_output() and self._src_port is None:
            self._src_port = port
        elif port.is_input() and self._dst_port is None:
            self._dst_port = port
        else:
            raise PortConnectionError("Cannot connect to power of same type")
        self._connect()
        self.update()

    def update(self):
        if self._src_port is not None:
            self._is_bus = self._src_port.width > 1
            src_comp = self._app_model.get_placed_component(self._src_port.parent())
            self._src_point = src_comp.pos + src_comp.get_port_pos(self._src_port.name())
        if self._dst_port is not None:
            self._is_bus = self._dst_port.width > 1
            dst_comp = self._app_model.get_placed_component(self._dst_port.parent())
            self._dst_point = dst_comp.pos + dst_comp.get_port_pos(self._dst_port.name())

    def is_close(self, point):
        if (
            point.x() < min(self._src_point.x(), self._dst_point.x())
            or point.x() > max(self._src_point.x(), self._dst_point.x())
            or point.y() < min(self._src_point.y(), self._dst_point.y())
            or point.y() > max(self._src_point.y(), self._dst_point.y())
        ):
            return False
        p1_x = self._src_point.x()
        p1_y = self._src_point.y()
        p2_x = self._dst_point.x()
        p2_y = self._dst_point.y()
        p3_x = point.x()
        p3_y = point.y()
        nom = abs((p2_x - p1_x) * (p1_y - p3_y) - (p1_x - p3_x) * (p2_y - p1_y))
        denom = math.sqrt((p2_x - p1_x) ** 2 + (p2_y - p1_y) ** 2)

        return (nom / denom) < self.WIRE_CLICK_CLOSE_PIXELS

    def has_port(self, port):
        return port in [self._src_port, self._dst_port]

    @property
    def key(self):
        return (self._src_port, self._dst_port)

    @property
    def src_port(self):
        return self._src_port

    @property
    def dst_port(self):
        return self._dst_port

    @property
    def start_pos(self):
        if self._src_point is not None:
            return self._src_point
        return self._dst_point
