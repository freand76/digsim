# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

""" A component placed in the GUI """

# pylint: disable=too-many-public-methods
# pylint: disable=too-many-instance-attributes

import abc

from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtGui import QFont, QFontMetrics, QPen
from PySide6.QtWidgets import QMenu

from ._component_item import ComponentGraphicsItem

class ComponentContextMenu(QMenu):
    """The component contextmenu class"""

    def __init__(self, parent, app_model, component_object):
        super().__init__(parent)
        self._app_model = app_model
        self._component_object = component_object
        self._component = self._component_object.component
        self._reconfigurable_parameters = None
        # Title
        titleAction = QAction(self._component.display_name(), self)
        titleAction.setEnabled(False)
        self.addAction(titleAction)
        self.addSeparator()
        # Settings
        self._add_settings()
        self._component_object.add_context_menu_action(self, parent)
        self.addSeparator()
        # Bring to front / Send to back
        raiseAction = QAction("Bring to front", self)
        self.addAction(raiseAction)
        raiseAction.triggered.connect(self._raise)
        lowerAction = QAction("Send to back", self)
        self.addAction(lowerAction)
        lowerAction.triggered.connect(self._lower)
        self.addSeparator()
        # Delete
        deleteAction = QAction("Delete", self)
        self.addAction(deleteAction)
        deleteAction.triggered.connect(self._delete)
        self._menu_action = None

    def _add_settings(self):
        self._reconfigurable_parameters = self._component.get_reconfigurable_parameters()
        if len(self._reconfigurable_parameters) > 0:
            settingsAction = QAction("Settings", self)
            self.addAction(settingsAction)
            settingsAction.triggered.connect(self._settings)

    def create(self, position):
        """Create context menu for component"""
        self._menu_action = self.exec_(position)

    def get_action(self):
        """Get context menu action"""
        return self._menu_action.text() if self._menu_action is not None else ""

    def _delete(self):
        self._component_object.select(True)
        self._app_model.objects.delete_selected()

    def _raise(self):
        self._app_model.objects.components.bring_to_front(self._component_object)

    def _lower(self):
        self._app_model.objects.components.send_to_back(self._component_object)

    def _settings(self):
        """Start the settings dialog for reconfiguration"""
        ok, settings = ComponentSettingsDialog.start(
            self._parent,
            self._app_model,
            self._component.name(),
            self._reconfigurable_parameters,
        )
        if ok:
            self._app_model.objects.components.update_settings(self._component_object, settings)


class ComponentObject(ComponentGraphicsItem):
    """The base class for a component placed in the GUI"""

    DEFAULT_WIDTH = 120
    DEFAULT_HEIGHT = 100
    RECT_TO_BORDER = 5
    BORDER_TO_PORT = 30
    PORT_SIDE = 8
    PORT_CLICK_BOX_SIDE = 20
    MIN_PORT_TO_PORT_DISTANCE = 20

    def __init__(self, app_model, component, xpos, ypos):
        self._app_model = app_model
        self._component = component
        self._object_pos = QPoint(xpos, ypos)
        self._selected = False
        self._height = self.DEFAULT_HEIGHT
        self._width = self.DEFAULT_WIDTH
        self._port_rects = {}
        self._port_display_name = {}
        self.update_ports()
        super().__init__(app_model,
                         QRect(self.object_pos, self.size),
                         self._port_rects,
                         self,
                         )
        
    def select(self, selected=True):
        """Set the selected variable for the current object"""
        self._selected = selected

    @property
    def selected(self):
        """Get the selected variable for the current object"""
        return self._selected

    def add_context_menu_action(self, menu, parent):
        """Add component specific context menu items"""

    def update_size(self):
        """update component object size"""

    def repaint(self):
        """Update GUI for this component object"""
        self._app_model.sig_repaint.emit()

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
    
    def paint(self, painter, option, widget=None):
        """QT function"""
        self.paint_component(painter)
        self.paint_ports(painter)

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
    def paint_selectable_component_name(cls, painter, point, size, name):
        """Paint the name for the selectable component"""
        font = QFont("Arial", 8)
        fm = QFontMetrics(font)
        str_pixels_w = fm.horizontalAdvance(name)
        str_pixels_h = fm.height()
        painter.setFont(font)
        painter.setPen(Qt.black)
        painter.drawText(
            point.x() + size.width() / 2 - str_pixels_w / 2,
            point.y() + size.height() - str_pixels_h,
            name,
        )

    def inport_x_pos(self):
        """Get the X position left of the input port"""
        return 1.5 * self.PORT_SIDE

    def paint_ports(self, painter):
        """Paint component ports"""
        painter.setPen(Qt.black)
        font = QFont("Arial", 8)
        painter.setFont(font)
        fm = QFontMetrics(font)
        for portname, rect in self._port_rects.items():
            port_str, str_pixels_w, str_pixels_h = self.get_port_display_name_metrics(portname)
            str_pixels_w = fm.horizontalAdvance(port_str)
            str_pixels_h = fm.height()
            text_y = rect.y() + str_pixels_h - self.PORT_SIDE / 2
            if rect.x() == self._object_pos.x():
                text_pos = QPoint(rect.x() + self.inport_x_pos(), text_y)
            else:
                text_pos = QPoint(rect.x() - str_pixels_w - self.PORT_SIDE / 2, text_y)
            painter.drawText(text_pos, port_str)

    def _add_port_rects(self, ports, xpos):
        if len(ports) == 1:
            self._port_rects[ports[0].name()] = QRect(
                self._object_pos.x() + xpos,
                self._object_pos.y() + self._height / 2 - self.PORT_SIDE / 2,
                self.PORT_SIDE,
                self.PORT_SIDE,
            )
        elif len(ports) > 1:
            port_distance = (self._height - 2 * self.BORDER_TO_PORT) / (len(ports) - 1)
            for idx, port in enumerate(ports):
                self._port_rects[port.name()] = QRect(
                    self._object_pos.x() + xpos,
                    self._object_pos.y()
                    + self.BORDER_TO_PORT
                    + idx * port_distance
                    - self.PORT_SIDE / 2,
                    self.PORT_SIDE,
                    self.PORT_SIDE,
                )

    def get_rect(self):
        """Get component rect"""
        return QRect(
            self._object_pos.x() + self.RECT_TO_BORDER,
            self._object_pos.y() + self.RECT_TO_BORDER,
            self._width - 2 * self.RECT_TO_BORDER,
            self._height - 2 * self.RECT_TO_BORDER,
        )

    def get_port_pos(self, portname):
        """Get component pos"""
        return self._port_rects[portname].center()

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

    @property
    def component(self):
        """Get component"""
        return self._component

    @property
    def size(self):
        """Get size"""
        return QSize(self._width, self._height)

    @property
    def object_pos(self):
        """Get position"""
        return self._object_pos

    @object_pos.setter
    def object_pos(self, point):
        """Set position"""
        self._object_pos = point
        self.update_ports()

    @property
    def zlevel(self):
        """Get zlevel"""
        return self.zValue()

    @zlevel.setter
    def zlevel(self, level):
        """Set zlevel"""
        self.setZValue(level)

    def to_dict(self):
        """Return position as dict"""
        return {"x": self._object_pos.x(), "y": self._object_pos.y(), "z": self.zlevel}

    def create_context_menu(self, parent, screen_position):
        context_menu = ComponentContextMenu(parent, self._app_model, self)
        context_menu.create(screen_position)
