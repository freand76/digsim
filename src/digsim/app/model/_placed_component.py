# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtGui import QFont, QFontMetrics, QPen

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

    def __init__(self, component, xpos, ypos):
        super().__init__()
        self._component = component
        self._pos = QPoint(xpos, ypos)
        self._height = self.DEFAULT_HEIGHT
        self._width = self.DEFAULT_WIDTH
        self._port_rects = {}
        self._port_display_name = {}
        self.update_ports()

    def update_ports(self):
        self._port_rects = {}
        self._port_display_name = {}
        self._add_port_rects(self._component.inports, 0)
        self._add_port_rects(self._component.outports, self._width - self.PORT_SIDE - 1)
        for port in self._component.ports:
            if port.width == 1:
                self._port_display_name[port.name] = port.name
            else:
                self._port_display_name[port.name] = f"{port.name}[{port.width}:0]"

    def get_port_display_name_metrics(self, portname):
        font = QFont("Arial", 8)
        fm = QFontMetrics(font)
        display_name_str = self._port_display_name[portname]
        str_pixels_w = fm.horizontalAdvance(display_name_str)
        str_pixels_h = fm.height()
        return display_name_str, str_pixels_w, str_pixels_h

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
        font = QFont("Arial", 8)
        painter.setFont(font)
        fm = QFontMetrics(font)
        display_name_str = self._component.display_name
        str_pixels_w = fm.horizontalAdvance(display_name_str)
        str_pixels_h = fm.height()
        painter.drawText(
            self.get_rect().x() + self.get_rect().width() / 2 - str_pixels_w / 2,
            self.get_rect().y() + str_pixels_h,
            display_name_str,
        )

    def inport_x_pos(self):
        return 1.5 * self.PORT_SIDE

    def paint_ports(self, painter, active_port):
        # Draw ports
        painter.setPen(Qt.black)
        painter.setBrush(Qt.SolidPattern)
        font = QFont("Arial", 8)
        painter.setFont(font)
        fm = QFontMetrics(font)
        for portname, rect in self._port_rects.items():
            if portname == active_port:
                painter.setBrush(Qt.red)
            else:
                painter.setBrush(Qt.gray)
            painter.drawRect(rect)
            port_str, str_pixels_w, str_pixels_h = self.get_port_display_name_metrics(portname)
            str_pixels_w = fm.horizontalAdvance(port_str)
            str_pixels_h = fm.height()
            text_y = rect.y() + str_pixels_h - self.PORT_SIDE / 2
            if rect.x() == 0:
                text_pos = QPoint(self.inport_x_pos(), text_y)
            else:
                text_pos = QPoint(rect.x() - str_pixels_w - self.PORT_SIDE / 2, text_y)
            painter.drawText(text_pos, port_str)

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
    def size(self):
        return QSize(self._width, self._height)

    @pos.setter
    def pos(self, point):
        self._pos = point

    def to_dict(self):
        return {"x": self.pos.x(), "y": self.pos.y()}
