# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

""" A component placed in the GUI """

# pylint: disable=unused-argument
# pylint: disable=too-many-public-methods
# pylint: disable=too-many-instance-attributes

import abc

from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtGui import QFont, QFontMetrics, QPen
from PySide6.QtWidgets import QGraphicsItem, QGraphicsRectItem

from ._component_context_menu import ComponentContextMenu
from ._component_port_item import PortGraphicsItem


class ComponentObject(QGraphicsRectItem):
    """A component graphics item, a 'clickable' item with a custom paintEvent"""

    DEFAULT_WIDTH = 120
    DEFAULT_HEIGHT = 100
    RECT_TO_BORDER = 5
    BORDER_TO_PORT = 30
    PORT_SIDE = 8
    MIN_PORT_TO_PORT_DISTANCE = 20

    def __init__(self, app_model, component, xpos, ypos):
        super().__init__(QRect(xpos, ypos, self.DEFAULT_WIDTH, self.DEFAULT_HEIGHT))
        self._app_model = app_model
        self._component = component

        # Class variables
        self._wire_items = []
        self._port_dict = {}
        self._parent = None
        self._mouse_press_pos = None
        self._moved = False
        self._save_pos = self.rect().topLeft()

        # Create ports
        self.create_ports()

        # Qt Flags
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)

    def itemChange(self, change, value):
        """QT event callback function"""
        if change == QGraphicsItem.ItemPositionChange:
            if self._app_model.is_running:
                value = QPoint(0, 0)
        elif change == QGraphicsItem.ItemPositionHasChanged:
            self._moved = True
        elif change == QGraphicsItem.ItemSelectedChange:
            if self._app_model.is_running:
                value = 0
        elif change == QGraphicsItem.ItemSelectedHasChanged:
            self._repaint()
        return super().itemChange(change, value)

    def hoverEnterEvent(self, _):
        """QT event callback function"""
        if self._app_model.is_running and self.component.has_action:
            self.setCursor(Qt.PointingHandCursor)

    def hoverLeaveEvent(self, _):
        """QT event callback function"""
        self.setCursor(Qt.ArrowCursor)

    def hoverMoveEvent(self, event):
        """QT event callback function"""
        self.mouse_position(event.scenePos())
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event):
        """QT event callback function"""
        super().mousePressEvent(event)
        if event.button() == Qt.LeftButton:
            if self._app_model.is_running:
                self._app_model.model_add_event(self.component.onpress)
            else:
                self._mouse_press_pos = event.screenPos()
                self.setCursor(Qt.ClosedHandCursor)

    def mouseReleaseEvent(self, event):
        """QT event callback function"""
        super().mouseReleaseEvent(event)
        if event.button() == Qt.LeftButton:
            if self._app_model.is_running:
                self._app_model.model_add_event(self.component.onrelease)
            else:
                self.setCursor(Qt.ArrowCursor)
                if event.screenPos() != self._mouse_press_pos:
                    # Move completed, set model to changed
                    self._app_model.objects.components.component_moved()
                    position = self.rect().topLeft() + self.pos()
                    self._save_pos = position.toPoint()
                else:
                    if not self._app_model.objects.new_wire.ongoing():
                        self.single_click_action()
        self._mouse_press_pos = None

    def contextMenuEvent(self, event):
        """QT event callback function"""
        if self._app_model.is_running:
            return
        if self._app_model.objects.new_wire.ongoing():
            self._app_model.objects.new_wire.abort()
        context_menu = ComponentContextMenu(self._parent, self._app_model, self)
        context_menu.create(event.screenPos())

    def paint(self, painter, option, widget=None):
        """QT function"""
        self.paint_component(painter)
        self.paint_ports(painter)

    @property
    def component(self):
        """Get component"""
        return self._component

    def has_moved(self):
        """True if the component has moved since last call"""
        moved = self._moved
        self._moved = False
        return moved

    def create_ports(self):
        """Create ports for component object"""
        for port in self._component.ports:
            self._port_dict[port] = {}
            if port.width == 1:
                self._port_dict[port]["name"] = port.name()
            else:
                self._port_dict[port]["name"] = f"{port.name()}[{port.width-1}:0]"
            item = PortGraphicsItem(self._app_model, self, port)
            self._port_dict[port]["item"] = item
        self.update_ports()

    def update_ports(self):
        """Update port positions for the placed component"""
        max_ports = max(len(self._component.inports()), len(self._component.outports()))
        if max_ports > 1:
            min_height = (
                (max_ports - 1) * self.MIN_PORT_TO_PORT_DISTANCE
                + 2 * self.BORDER_TO_PORT
                + 2 * self.RECT_TO_BORDER
            )
            self.height = max(self.height, min_height)
        self._set_port_rects(self._component.inports(), 0)
        self._set_port_rects(self._component.outports(), self.width - self.PORT_SIDE - 1)

    def get_port_item(self, port):
        """Get port item"""
        return self._port_dict[port]["item"]

    def set_port_rect(self, port, rect):
        """Set port rect"""
        self.get_port_item(port).setRect(rect)

    def _set_port_rects(self, ports, xpos):
        if len(ports) == 1:
            rect = QRect(
                self.object_pos.x() + xpos,
                self.object_pos.y() + self.height / 2 - self.PORT_SIDE / 2,
                self.PORT_SIDE,
                self.PORT_SIDE,
            )
            self._port_dict[ports[0]]["item"].setRect(rect)
        elif len(ports) > 1:
            port_distance = (self.height - 2 * self.BORDER_TO_PORT) / (len(ports) - 1)
            for idx, port in enumerate(ports):
                rect = QRect(
                    self.object_pos.x() + xpos,
                    self.object_pos.y()
                    + self.BORDER_TO_PORT
                    + idx * port_distance
                    - self.PORT_SIDE / 2,
                    self.PORT_SIDE,
                    self.PORT_SIDE,
                )
                self._port_dict[port]["item"].setRect(rect)

    def set_parent_view(self, parent):
        """Set the parent"""
        self._parent = parent

    def clear_wires(self):
        """Add wire_item to component"""
        self._wire_items = []

    def add_wire(self, wire):
        """Add wire_item to component"""
        self._wire_items.append(wire)

    def _repaint(self):
        """Make scene repaint for component update"""
        self._app_model.sig_repaint.emit()

    @property
    def selected(self):
        """Get the selected variable for the current object"""
        return self.isSelected()

    def repaint(self):
        """Update GUI for this component object"""
        self._app_model.sig_repaint.emit()

    def get_port_display_name_metrics(self, port_str):
        """Get the port display name (including bits if available)"""
        font = QFont("Arial", 8)
        fm = QFontMetrics(font)
        str_pixels_w = fm.horizontalAdvance(port_str)
        str_pixels_h = fm.height()
        return str_pixels_w, str_pixels_h

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
        for port in self._component.ports:
            rect = self._port_dict[port]["item"].rect()
            port_str = self._port_dict[port]["name"]
            str_pixels_w, str_pixels_h = self.get_port_display_name_metrics(port_str)
            text_y = rect.y() + str_pixels_h - self.PORT_SIDE / 2
            if rect.x() == self.object_pos.x():
                text_pos = QPoint(rect.x() + self.inport_x_pos(), text_y)
            else:
                text_pos = QPoint(rect.x() - str_pixels_w - self.PORT_SIDE / 2, text_y)
            painter.drawText(text_pos, port_str)

    def get_rect(self):
        """Get component rect, excluding border where ports are"""
        return QRect(
            self.rect().x() + self.RECT_TO_BORDER,
            self.rect().y() + self.RECT_TO_BORDER,
            self.rect().width() - 2 * self.RECT_TO_BORDER,
            self.rect().height() - 2 * self.RECT_TO_BORDER,
        )

    def get_port_pos(self, portname):
        """Get component port pos"""
        port = self.component.port(portname)
        return self._port_dict[port]["item"].rect().center()

    def mouse_position(self, pos):
        """Component function: called for mouse position update"""

    def single_click_action(self):
        """Component function:: called for mouse single click"""

    def add_context_menu_action(self, menu, parent):
        """Component function:: called when context menu is created"""

    def update_size(self):
        """Component function: called when the component can update its size"""

    @property
    def size(self):
        """Get size"""
        return QSize(self.width, self.height)

    @property
    def object_pos(self):
        """Get position"""
        return self.rect().topLeft()

    @property
    def width(self):
        """Get width"""
        return self.rect().width()

    @width.setter
    def width(self, width):
        """Set width"""
        self.setRect(self.rect().x(), self.rect().y(), width, self.rect().height())

    @property
    def height(self):
        """Get height"""
        return self.rect().height()

    @height.setter
    def height(self, height):
        """Set height"""
        self.setRect(self.rect().x(), self.rect().y(), self.rect().width(), height)

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
        return {"x": self._save_pos.x(), "y": self._save_pos.y(), "z": self.zlevel}
