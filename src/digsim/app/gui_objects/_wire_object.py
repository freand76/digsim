# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

""" A wire placed in the GUI """

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QPainterPath, QPen

from digsim.circuit.components.atoms import PortConnectionError

from ._gui_object import GuiObject


class WireObject(GuiObject):
    """The class for wire placed in the GUI"""

    WIRE_CLICK_CLOSE_PIXELS = 10
    WIRE_TO_OBJECT_DIST = 5

    def __init__(self, app_model, port_a, port_b=None, connect=True):
        super().__init__()
        self._app_model = app_model
        self._src_port = None
        self._dst_port = None
        self._line_path = []
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

    def _is_bus(self):
        if self._src_port is not None:
            return self._src_port.width > 1
        return self._dst_port.width > 1

    def _create_line(self, src, dst):
        self._line_path = []
        if self._src_port is not None:
            component_object = self._app_model.objects.components.get_object(
                self._src_port.parent()
            )
            source = src
            dest = dst
        else:
            source = dst
            dest = src
            component_object = self._app_model.objects.components.get_object(
                self._dst_port.parent()
            )

        component_top_y = component_object.pos.y()
        component_bottom_y = component_object.pos.y() + component_object.size.height()

        self._line_path.append(source)
        if source.x() < dest.x():
            half_dist_x = (dest.x() - source.x()) / 2
            self._line_path.append(QPoint(source.x() + half_dist_x, source.y()))
            self._line_path.append(QPoint(source.x() + half_dist_x, source.y()))
            self._line_path.append(QPoint(source.x() + half_dist_x, dest.y()))
            self._line_path.append(QPoint(dest.x(), dest.y()))
        else:
            half_dist_y = (dest.y() - source.y()) / 2
            if dst.y() > src.y():
                y_mid = max(
                    component_bottom_y - source.y() + self.WIRE_TO_OBJECT_DIST, half_dist_y
                )
            else:
                y_mid = min(component_top_y - source.y() - self.WIRE_TO_OBJECT_DIST, half_dist_y)
            self._line_path.append(QPoint(source.x() + 10, source.y()))
            self._line_path.append(QPoint(source.x() + 10, source.y() + y_mid))
            self._line_path.append(QPoint(dest.x() - 10, source.y() + y_mid))
            self._line_path.append(QPoint(dest.x() - 10, dest.y()))
        self._line_path.append(QPoint(dest.x(), dest.y()))

    def _paint_wire(self, painter):
        pen = QPen()
        pen.setColor(Qt.darkGray)

        if self._is_bus():
            pen.setWidth(4)
        else:
            pen.setWidth(2)

        color_wires = self._app_model.settings.get("color_wires")
        if color_wires and self._src_port is not None and self._src_port.value != 0:
            value = self._src_port.value if self._src_port.value != "X" else 0
            max_value = 2**self._src_port.width - 1
            pen.setColor(QColor(0, 255 * value / max_value, 0))
        else:
            pen.setColor(Qt.black)

        if self.selected:
            pen.setWidth(6)

        painter.setPen(pen)
        path = QPainterPath(self._line_path[0])
        for point in self._line_path[1:]:
            path.lineTo(point)
        painter.drawPath(path)

    def paint(self, painter):
        """Paint paced wire"""
        self._paint_wire(painter)

    def paint_new(self, painter, end_pos):
        """Paint new/unfinished placed wire"""
        self._create_line(self.start_pos, end_pos)
        self._paint_wire(painter)

    def _connect(self):
        if self._src_port is not None and self._dst_port is not None:
            self._src_port.wire = self._dst_port

    def disconnect(self):
        """Disconnect placed wire"""
        self._src_port.disconnect(self._dst_port)

    def set_end_port(self, port):
        """Set end port when creating a new wire"""
        if port.is_output() and self._src_port is None:
            self._src_port = port
        elif port.is_input() and self._dst_port is None:
            self._dst_port = port
        else:
            raise PortConnectionError("Cannot connect to power of same type")
        self._connect()
        self.update()

    def update(self):
        """Update the wire position if the connected components move"""
        if self._src_port is not None:
            src_comp = self._app_model.objects.components.get_object(self._src_port.parent())
            self._src_point = src_comp.pos + src_comp.get_port_pos(self._src_port.name())
        if self._dst_port is not None:
            dst_comp = self._app_model.objects.components.get_object(self._dst_port.parent())
            self._dst_point = dst_comp.pos + dst_comp.get_port_pos(self._dst_port.name())
        if self._src_port is not None and self._dst_port is not None:
            self._create_line(self._src_point, self._dst_point)

    def is_close(self, point):
        """Return True if the point is close to this wire, used for selection"""

        for idx, point1 in enumerate(self._line_path[0:-2]):
            point2 = self._line_path[idx + 1]
            point1_x = min(
                point1.x() - self.WIRE_CLICK_CLOSE_PIXELS,
                point2.x() - self.WIRE_CLICK_CLOSE_PIXELS,
            )
            point1_y = min(
                point1.y() - self.WIRE_CLICK_CLOSE_PIXELS,
                point2.y() - self.WIRE_CLICK_CLOSE_PIXELS,
            )
            point2_x = max(
                point1.x() + self.WIRE_CLICK_CLOSE_PIXELS,
                point2.x() + self.WIRE_CLICK_CLOSE_PIXELS,
            )
            point2_y = max(
                point1.y() + self.WIRE_CLICK_CLOSE_PIXELS,
                point2.y() + self.WIRE_CLICK_CLOSE_PIXELS,
            )
            if point.x() > point1_x and point.x() < point2_x:
                if point.y() > point1_y and point.y() < point2_y:
                    return True
        return False

    def in_rect(self, rect):
        if self._src_point is not None and self._dst_point is not None:
            return self.point_in_rect(self._src_point, rect) and self.point_in_rect(
                self._dst_point, rect
            )
        return False

    def has_port(self, port):
        """Return True if port is alredy a part of this wire?"""
        return port in [self._src_port, self._dst_port]

    @property
    def key(self):
        """Get placed wire key, used by the model"""
        return (self._src_port, self._dst_port)

    @property
    def src_port(self):
        """Get the source port of the placed wire"""
        return self._src_port

    @property
    def dst_port(self):
        """Get the destination port of the placed wire"""
        return self._dst_port

    @property
    def start_pos(self):
        """Get the start point for the unfinished placed wire"""
        if self._src_point is not None:
            return self._src_point
        return self._dst_point
