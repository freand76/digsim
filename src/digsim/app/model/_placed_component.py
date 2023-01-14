# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtGui import QFont, QPen

from ._placed_object import PlacedObject


class CompenentException(Exception):
    pass


class PlacedComponent(PlacedObject):

    DEFAULT_WIDTH = 120
    DEFAULT_HEIGHT = 100
    BORDER_MARGIN = 20
    PORT_SIDE = 8
    COMPONENT_BORDER = 5
    PORT_CLICK_EXTRA_PIXELS = 10

    def __init__(self, component, xpos, ypos, settings=False):
        super().__init__()
        self._component = component
        self._pos = QPoint(xpos, ypos)
        self._settings = settings
        self._height = self.DEFAULT_HEIGHT
        self._width = self.DEFAULT_WIDTH
        self._port_rects = {}
        self.update_ports()

    def update_ports(self):
        self._port_rects = {}
        self._add_port_rects(self._component.inports, 0)
        self._add_port_rects(self._component.outports, self._width - self.PORT_SIDE - 1)

    def paint_component_base(self, painter):
        # Draw component
        comp_rect = self.get_rect()
        pen = QPen()
        if self.selected:
            pen.setWidth(4)
        else:
            pen.setWidth(1)
        pen.setColor(Qt.black)
        painter.setPen(pen)
        painter.setBrush(Qt.SolidPattern)
        if self.component.active:
            painter.setBrush(Qt.green)
        else:
            painter.setBrush(Qt.gray)
        painter.drawRoundedRect(comp_rect, 5, 5)

    def paint_component(self, painter):
        self.paint_component_base(painter)
        painter.setFont(QFont("Arial", 8))
        painter.drawText(self.get_rect(), Qt.AlignCenter, self._component.display_name)

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
            painter.drawText(rect.x(), rect.y(), portname)

    def _add_port_rects(self, ports, xpos):
        if len(ports) == 1:
            self._port_rects[ports[0].name] = QRect(
                xpos,
                self._height / 2 - self.PORT_SIDE / 2,
                self.PORT_SIDE,
                self.PORT_SIDE,
            )
        elif len(ports) > 1:
            port_distance = (self._height - 2 * self.BORDER_MARGIN) / (len(ports) - 1)
            for idx, port in enumerate(ports):
                self._port_rects[port.name] = QRect(
                    xpos,
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

    def create_context_menu(self, parent, event):
        pass

    @property
    def component(self):
        return self._component

    @property
    def pos(self):
        return self._pos

    @property
    def settings(self):
        return self._settings

    @property
    def size(self):
        return QSize(self._width, self._height)

    @pos.setter
    def pos(self, point):
        self._pos = point

    def settings_dict(self):
        return {}

    def to_dict(self):
        return {"x": self.pos.x(), "y": self.pos.y()}
