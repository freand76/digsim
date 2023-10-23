# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

""" A component graphics item """

# pylint: disable=unused-argument
# pylint: disable=useless-parent-delegation

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QBrush, QPen
from PySide6.QtWidgets import QGraphicsItem, QGraphicsRectItem

from digsim.circuit.components.atoms import PortConnectionError


class PortGraphicsItem(QGraphicsRectItem):
    """A port graphics item"""

    def __init__(self, app_model, parent, port):
        super().__init__(QRect(0, 0, 0, 0), parent)
        self._app_model = app_model
        self._port = port
        self.setPen(QPen(Qt.black))
        self.setBrush(Qt.SolidPattern)
        self.setBrush(QBrush(Qt.gray))
        self.setAcceptHoverEvents(True)

    def _repaint(self):
        """Make scene repaint for component update"""
        self._app_model.sig_repaint.emit()

    def mousePressEvent(self, event):
        """QT event callback function"""
        if self._app_model.objects.new_wire.ongoing():
            try:
                self._app_model.objects.new_wire.end(self._port.parent(), self._port.name())
            except PortConnectionError as exc:
                self._app_model.objects.new_wire.abort()
                self._app_model.sig_error.emit(str(exc))
                self._repaint()
        else:
            self._app_model.objects.new_wire.start(self._port.parent(), self._port.name())

    def hoverEnterEvent(self, _):
        """QT event callback function"""
        if self._app_model.is_running:
            return
        self.setBrush(QBrush(Qt.red))
        self.setCursor(Qt.CrossCursor)
        self._repaint()

    def hoverLeaveEvent(self, _):
        """QT event callback function"""
        if self._app_model.is_running:
            return
        self.setBrush(QBrush(Qt.gray))
        self.setCursor(Qt.ArrowCursor)
        self._repaint()

    def portParentRect(self):
        """return the parent position"""
        return self.parentItem().rect().translated(self.parentItem().pos())

    def portPos(self):
        """return the parent position"""
        return self.parentItem().pos() + self.rect().center()


class ComponentGraphicsItem(QGraphicsRectItem):
    """A component graphics item, a 'clickable' item with a custom paintEvent"""

    def __init__(self, app_model, rect):
        super().__init__(rect)
        self._parent = None
        self._app_model = app_model
        self._wire_items = []
        self._port_dict = {}
        self._mouse_press_pos = None
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)
        self._save_pos = self.rect().topLeft()
        self._moved = False

    def has_moved(self):
        """True if the component has moved since last call"""
        moved = self._moved
        self._moved = False
        return moved

    def create_port_item(self, port):
        """Create port graphics item"""
        item = PortGraphicsItem(self._app_model, self, port)
        self._port_dict[port] = item

    def set_port_rect(self, port, rect):
        """Set port rect"""
        self._port_dict[port].setRect(rect)

    def get_port_rect(self, port):
        """Get port rect"""
        return self._port_dict[port].rect()

    def mouse_position(self, pos):
        """update component with mouse position"""

    def single_click_action(self):
        """Handle singleclick events"""

    def create_context_menu(self, parent, screen_position):
        """Create context menu"""

    def set_parent_view(self, parent):
        """Set the parent"""
        self._parent = parent

    def clear_wires(self):
        """Add wire_item to component"""
        self._wire_items = []

    def add_wire(self, wire):
        """Add wire_item to component"""
        self._wire_items.append(wire)

    def get_port_item(self, port):
        """Get port_item from component"""
        return self._port_dict[port]

    def _repaint(self):
        """Make scene repaint for component update"""
        self._app_model.sig_repaint.emit()

    def setSelected(self, selected):
        """Qt function"""
        super().setSelected(selected)

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
        """Create conext menu for component"""
        if self._app_model.is_running:
            return
        if self._app_model.objects.new_wire.ongoing():
            self._app_model.objects.new_wire.abort()
        self.create_context_menu(self._parent, event.screenPos())

    @property
    def save_pos(self):
        """Return the save position (will be updated after component move)"""
        return self._save_pos
