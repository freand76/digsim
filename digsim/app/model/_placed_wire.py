from digsim import PortDirection
from PySide6.QtCore import Qt
from PySide6.QtGui import QPen


class PlacedWire:
    def __init__(self, app_model, port_a, port_b=None):
        self._app_model = app_model
        self._src_port = None
        self._dst_port = None
        self._connected = False
        self._is_bus = False

        if port_a is None:
            raise Exception("Cannot start a wire without a port")

        if port_b is not None:
            if port_a.direction == PortDirection.OUT and port_b.direction == PortDirection.IN:
                self._src_port = port_a
                self._dst_port = port_b
            elif port_a.direction == PortDirection.IN and port_b.direction == PortDirection.OUT:
                self._src_port = port_b
                self._dst_port = port_a
            else:
                raise Exception("Cannot connect to power of same type")
        else:
            if port_a.direction == PortDirection.OUT:
                self._src_port = port_a
            else:
                self._dst_port = port_a

        self._src_point = None
        self._dst_point = None
        self.update()
        self.connect()

    def _paint_wire(self, painter, src, dst):
        pen = QPen()
        if self._is_bus:
            pen.setWidth(4)
        else:
            pen.setWidth(2)
        pen.setColor(Qt.darkGray)
        painter.setPen(pen)
        painter.drawLine(src, dst)

    def paint(self, painter):
        self._paint_wire(painter, self._src_point, self._dst_point)

    def paint_new(self, painter, end_pos):
        self._paint_wire(painter, self.start_pos, end_pos)

    def connect(self):
        if self._src_port is not None and self._dst_port is not None:
            self._src_port.wire = self._dst_port
            self._connected = True

    def set_end_port(self, port):
        if port.direction == PortDirection.OUT and self._src_port is None:
            self._src_port = port
        elif port.direction == PortDirection.IN and self._dst_port is None:
            self._dst_port = port
        else:
            raise Exception("Cannot connect to power of same type")

        self.update()

    def update(self):
        if self._src_port is not None:
            self._is_bus = self._src_port.width > 1
            src_comp = self._app_model.get_placed_component(self._src_port.parent)
            self._src_point = src_comp.pos + src_comp.get_port_pos(self._src_port.name)
        if self._dst_port is not None:
            self._is_bus = self._dst_port.width > 1
            dst_comp = self._app_model.get_placed_component(self._dst_port.parent)
            self._dst_point = dst_comp.pos + dst_comp.get_port_pos(self._dst_port.name)

    @property
    def src_port(self):
        return self._src_port

    @property
    def dst_port(self):
        return self._dst_port

    @property
    def src(self):
        return self._src_point

    @property
    def dst(self):
        return self._dst_point

    @property
    def start_pos(self):
        if self._src_point is not None:
            return self._src_point
        return self._dst_point
