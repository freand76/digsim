# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

""" A component placed in the GUI """

import abc
from functools import partial

from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtGui import QAction, QFont, QFontMetrics, QPen
from PySide6.QtWidgets import QMenu

from digsim.app.gui._component_settings import ComponentSettingsDialog

from ._gui_object import GuiObject


class ComponentObject(GuiObject):
    """The base class for a component placed in the GUI"""

    DEFAULT_WIDTH = 120
    DEFAULT_HEIGHT = 100
    RECT_TO_BORDER = 5
    BORDER_TO_PORT = 30
    PORT_SIDE = 8
    PORT_CLICK_BOX_SIDE = 20
    MIN_PORT_TO_PORT_DISTANCE = 20

    def __init__(self, component, xpos, ypos):
        super().__init__()
        self._component = component
        self._pos = QPoint(xpos, ypos)
        self._height = self.DEFAULT_HEIGHT
        self._width = self.DEFAULT_WIDTH
        self._port_rects = {}
        self._port_display_name = {}
        self.update_ports()

    def center(self):
        """move component so pos is center instead of top-left corner"""
        self._pos = self._pos - QPoint(self._width / 2, self._height / 2)

    def update_ports(self):
        """Update port positions for the placed component"""
        max_ports = max(len(self._component.inports()), len(self._component.outports()))
        if max_ports > 1:
            min_height = (
                (max_ports - 1) * self.MIN_PORT_TO_PORT_DISTANCE
                + 2 * self.BORDER_TO_PORT
                + 2 * self.RECT_TO_BORDER
            )
            self._height = max(self._height, min_height)
        self._port_rects = {}
        self._port_display_name = {}
        self._add_port_rects(self._component.inports(), 0)
        self._add_port_rects(self._component.outports(), self._width - self.PORT_SIDE - 1)
        for port in self._component.ports:
            if port.width == 1:
                self._port_display_name[port.name()] = port.name()
            else:
                self._port_display_name[port.name()] = f"{port.name()}[{port.width-1}:0]"

    def get_port_display_name_metrics(self, portname):
        """Get the port display name (including bits if available"""
        font = QFont("Arial", 8)
        fm = QFontMetrics(font)
        display_name_str = self._port_display_name[portname]
        str_pixels_w = fm.horizontalAdvance(display_name_str)
        str_pixels_h = fm.height()
        return display_name_str, str_pixels_w, str_pixels_h

    def paint_component_name(self, painter):
        """Paint the component name"""
        font = QFont("Arial", 10)
        painter.setFont(font)
        fm = QFontMetrics(font)
        display_name_str = self._component.display_name()
        str_pixels_w = fm.horizontalAdvance(display_name_str)
        str_pixels_h = fm.height()
        painter.drawText(
            self.get_rect().x() + self.get_rect().width() / 2 - str_pixels_w / 2,
            self.get_rect().y() + str_pixels_h,
            display_name_str,
        )

    def paint_component_base(self, painter):
        """Paint component base rect"""
        comp_rect = self.get_rect()
        pen = QPen()
        if self.selected:
            pen.setWidth(4)
        else:
            pen.setWidth(1)
        pen.setColor(Qt.black)
        painter.setPen(pen)
        painter.setBrush(Qt.SolidPattern)
        painter.setBrush(Qt.gray)
        painter.drawRoundedRect(comp_rect, 5, 5)

    @abc.abstractmethod
    def paint_component(self, painter):
        """Paint component"""

    @classmethod
    @abc.abstractmethod
    def paint_selectable_component(cls, painter, size, name):
        """
        Paint selectable component
        use width x width (square) to paint component image
        """

    @classmethod
    def paint_selectable_component_name(cls, painter, size, name):
        """Paint the name for the selectable component"""
        font = QFont("Arial", 8)
        fm = QFontMetrics(font)
        str_pixels_w = fm.horizontalAdvance(name)
        str_pixels_h = fm.height()
        painter.setFont(font)
        painter.setPen(Qt.black)
        painter.drawText(
            size.width() / 2 - str_pixels_w / 2,
            size.height() - str_pixels_h,
            name,
        )

    def inport_x_pos(self):
        """Get the X position left of the input port"""
        return 1.5 * self.PORT_SIDE

    def paint_ports(self, painter, active_port):
        """Paint component ports"""
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
            self._port_rects[ports[0].name()] = QRect(
                xpos,
                self._height / 2 - self.PORT_SIDE / 2,
                self.PORT_SIDE,
                self.PORT_SIDE,
            )
        elif len(ports) > 1:
            port_distance = (self._height - 2 * self.BORDER_TO_PORT) / (len(ports) - 1)
            for idx, port in enumerate(ports):
                self._port_rects[port.name()] = QRect(
                    xpos,
                    self.BORDER_TO_PORT + idx * port_distance - self.PORT_SIDE / 2,
                    self.PORT_SIDE,
                    self.PORT_SIDE,
                )

    def get_rect(self):
        """Get component rect"""
        return QRect(
            self.RECT_TO_BORDER,
            self.RECT_TO_BORDER,
            self._width - 2 * self.RECT_TO_BORDER,
            self._height - 2 * self.RECT_TO_BORDER,
        )

    def get_port_pos(self, portname):
        """Get component pos"""
        rect = self._port_rects[portname]
        return QPoint(rect.x(), rect.y()) + QPoint(self.PORT_SIDE / 2, self.PORT_SIDE / 2)

    def get_port_for_point(self, point):
        """Get component port from a point"""
        for portname, rect in self._port_rects.items():
            if (
                point.x() > rect.x() - self.PORT_CLICK_BOX_SIDE / 2
                and point.x() < rect.x() + rect.width() + self.PORT_CLICK_BOX_SIDE / 2
                and point.y() > rect.y() - self.PORT_CLICK_BOX_SIDE / 2
                and point.y() < rect.y() + rect.height() + self.PORT_CLICK_BOX_SIDE / 2
            ):
                return portname
        return None

    def create_context_menu(self, parent, position):
        """Create context menu for component"""
        reconfigurable_parameters = self._component.get_reconfigurable_parameters()
        action_list = {}
        if len(reconfigurable_parameters) > 0:
            action_list["Settings"] = partial(
                self.settings_dialog, parent, reconfigurable_parameters
            )

        if len(action_list) > 0:
            menu = QMenu(parent)
            for action in action_list:
                menu.addAction(QAction(action, parent))
            menu_action = menu.exec_(position)
            if menu_action is not None:
                action_list[menu_action.text()]()

    def settings_dialog(self, parent, reconfigurable_parameters):
        """Start the settings dialog for reconfiguration"""
        ok, settings = ComponentSettingsDialog.start(
            parent,
            parent.app_model(),
            self._component.name(),
            reconfigurable_parameters,
        )
        if ok:
            self._component.update_settings(settings)
            parent.app_model().set_changed()

    @property
    def component(self):
        """Get component"""
        return self._component

    @property
    def pos(self):
        """Get position"""
        return self._pos

    @property
    def size(self):
        """Get size"""
        return QSize(self._width, self._height)

    def in_rect(self, rect):
        top_left = self.pos
        bottom_right = QPoint(self.pos.x() + self.size.width(), self.pos.y() + self.size.height())
        return self.point_in_rect(top_left, rect) and self.point_in_rect(bottom_right, rect)

    @pos.setter
    def pos(self, point):
        """Set position"""
        self._pos = point

    def to_dict(self):
        """Return position as dict"""
        return {"x": self.pos.x(), "y": self.pos.y()}
