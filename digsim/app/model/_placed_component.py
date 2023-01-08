from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtGui import QFont


class PlacedComponent:

    DEFAULT_WIDTH = 120
    DEFAULT_HEIGHT = 100
    BORDER_MARGIN = 20
    PORT_SIDE = 8
    COMPONENT_BORDER = 5
    PORT_CLICK_EXTRA_PIXELS = 10

    def __init__(self, component, x, y):
        self._component = component
        self._pos = QPoint(x, y)
        self._height = self.DEFAULT_HEIGHT
        self._width = self.DEFAULT_WIDTH
        self._port_rects = {}
        self._add_port_rects(self._component.inports, 0)
        self._add_port_rects(self._component.outports, self._width - self.PORT_SIDE - 1)

    def paint_component_base(self, painter):
        # Draw component
        comp_rect = self.get_rect()
        painter.setPen(Qt.black)
        painter.setBrush(Qt.SolidPattern)
        if self.component.active:
            painter.setBrush(Qt.green)
        else:
            painter.setBrush(Qt.gray)
        painter.drawRoundedRect(comp_rect, 5, 5)

    def paint_component(self, painter):
        self.paint_component_base(painter)
        painter.setFont(QFont("Arial", 8))
        painter.drawText(self.get_rect(), Qt.AlignCenter, self._component.name)

    def paint_ports(self, painter, active_port):
        # Draw ports
        painter.setPen(Qt.black)
        painter.setBrush(Qt.SolidPattern)
        painter.setFont(QFont("Arial", 8))
        for portname, rect in self._port_rects.items():
            if portname == active_port:
                painter.setBrush(Qt.red)
            else:
                painter.setBrush(Qt.gray)
            painter.drawRect(rect)

    def _add_port_rects(self, ports, x):
        if len(ports) == 1:
            self._port_rects[ports[0].name] = QRect(
                x,
                self._height / 2 - self.PORT_SIDE / 2,
                self.PORT_SIDE,
                self.PORT_SIDE,
            )
        elif len(ports) > 1:
            port_distance = (self._height - 2 * self.BORDER_MARGIN) / (len(ports) - 1)
            for idx, port in enumerate(ports):
                self._port_rects[port.name] = QRect(
                    x,
                    self.BORDER_MARGIN + idx * port_distance - self.PORT_SIDE / 2,
                    self.PORT_SIDE,
                    self.PORT_SIDE,
                )

    def get_rect(self):
        return QRect(
            self.COMPONENT_BORDER,
            self.COMPONENT_BORDER,
            self._width - 2 * self.COMPONENT_BORDER,
            self._height - 2 * self.COMPONENT_BORDER,
        )

    def get_port_pos(self, portname):
        rect = self._port_rects[portname]
        return QPoint(rect.x(), rect.y()) + QPoint(self.PORT_SIDE / 2, self.PORT_SIDE / 2)

    def get_port_for_point(self, point):
        for portname, rect in self._port_rects.items():
            if (
                point.x() > rect.x() - self.PORT_CLICK_EXTRA_PIXELS
                and point.x() < rect.x() + rect.width() + self.PORT_CLICK_EXTRA_PIXELS
                and point.y() > rect.y() - self.PORT_CLICK_EXTRA_PIXELS
                and point.y() < rect.y() + rect.height() + self.PORT_CLICK_EXTRA_PIXELS
            ):
                return portname
        return None

    @property
    def component(self):
        return self._component

    @property
    def pos(self):
        return self._pos

    @property
    def size(self):
        return QSize(self._width, self._height)

    @pos.setter
    def pos(self, point):
        self._pos = point

    def __str__(self):
        return f'{{ "name": "{self.component.name}", "x": {self.pos.x()}, "y": {self.pos.y()} }}'
