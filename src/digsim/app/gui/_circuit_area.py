# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

"""The circuit area and component widget"""

from functools import partial

from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QPushButton, QWidget

from digsim.circuit.components.atoms import PortConnectionError

from ._component_settings import ComponentSettingsDialog


class ComponentWidget(QPushButton):
    """A component widget, a 'clickable' widget with a custom paintEvent"""

    def __init__(self, app_model, component_object, parent):
        super().__init__(parent, objectName=component_object.component.name())
        self._app_model = app_model
        self._app_model.sig_component_notify.connect(self._component_notify)
        self._component_object = component_object
        self._mouse_grab_pos = None
        self._active_port = None

        self.setMouseTracking(True)
        self.move(self._component_object.pos)

    def sizeHint(self):
        """QT event callback function"""
        return self._component_object.size

    @property
    def component(self):
        """Get component from widget"""
        return self._component_object.component

    def _component_notify(self, component):
        if component == self.component:
            self.update()

    def paintEvent(self, _):
        """QT event callback function"""
        painter = QPainter(self)
        self._component_object.paint_component(painter)
        self._component_object.paint_ports(painter, self._active_port)
        painter.end()

    def enterEvent(self, _):
        """QT event callback function"""
        if self._app_model.is_running and self.component.has_action:
            self.setCursor(Qt.PointingHandCursor)

    def leaveEvent(self, _):
        """QT event callback function"""
        self.setCursor(Qt.ArrowCursor)
        self._active_port = None

    def _new_wire_end(self):
        try:
            self._app_model.new_wire_end(self.component, self._active_port)
        except PortConnectionError as exc:
            self._app_model.new_wire_abort()
            self._app_model.sig_error.emit(str(exc))
            self.parent().update()

    def mousePressEvent(self, event):
        """QT event callback function"""
        super().mousePressEvent(event)
        if event.button() == Qt.LeftButton:
            if self._app_model.is_running:
                self._app_model.add_gui_event(self.component.onpress)
            elif self._app_model.has_new_wire():
                if self._active_port is not None:
                    self._new_wire_end()
            else:
                self._app_model.select(self._component_object)
                if self._active_port is None:
                    # Prepare to move
                    self.setCursor(Qt.ClosedHandCursor)
                    self._mouse_grab_pos = event.pos()
                else:
                    self._app_model.new_wire_start(self.component, self._active_port)
        elif event.button() == Qt.RightButton:
            if self._app_model.is_running:
                return
            if self._app_model.has_new_wire():
                self._app_model.new_wire_abort()
            else:
                self._component_object.create_context_menu(self, event)
                self.adjustSize()
                self.update()

    def mouseReleaseEvent(self, event):
        """QT event callback function"""
        super().mouseReleaseEvent(event)
        if event.button() == Qt.LeftButton:
            if self._app_model.is_running:
                self._app_model.add_gui_event(self.component.onrelease)
            else:
                # Move complete
                self.setCursor(Qt.ArrowCursor)
                self._mouse_grab_pos = None
                self._component_object.pos = self.pos()
                self._app_model.update_wires()
                self._app_model.set_changed()
                self.parent().update()

    def mouseMoveEvent(self, event):
        """QT event callback function"""
        if self._app_model.is_running:
            return

        active_port = self._component_object.get_port_for_point(event.pos())
        if active_port != self._active_port:
            self._active_port = active_port
            if self._active_port is not None:
                self.setCursor(Qt.CrossCursor)
            else:
                self.setCursor(Qt.ArrowCursor)
            self.update()

        if self._app_model.has_new_wire():
            end_pos = event.pos()
            if self._active_port:
                end_pos = self._component_object.get_port_pos(self._active_port)
            self._app_model.set_new_wire_end_pos(self.pos() + end_pos)
            self.parent().update()

        elif self._mouse_grab_pos is not None:
            self.move(self.pos() + event.pos() - self._mouse_grab_pos)
            self._component_object.pos = self.pos()
            self._app_model.update_wires()
            self.parent().update()


class CircuitArea(QWidget):
    """The circuit area class, this is where the component widgets are placed"""

    def __init__(self, app_model, parent):
        super().__init__(parent)
        self._app_model = app_model
        self._app_model.sig_update_gui_components.connect(self._update_gui_components)

        self.setMouseTracking(True)
        self.setAcceptDrops(True)

    def keyPressEvent(self, event):
        """QT event callback function"""
        if self._app_model.is_running:
            return
        if event.key() == Qt.Key_Delete:
            self._app_model.delete()
        event.accept()

    def paintEvent(self, _):
        """QT event callback function"""
        painter = QPainter(self)
        self._app_model.paint_wires(painter)
        painter.end()

    def mousePressEvent(self, event):
        """QT event callback function"""
        super().mousePressEvent(event)
        if event.button() == Qt.LeftButton:
            if self._app_model.is_running:
                return
            if self._app_model.has_new_wire():
                return
            self._app_model.select_pos(event.pos())
            self.setFocus()
            self.update()
        elif event.button() == Qt.RightButton:
            if self._app_model.is_running:
                return
            if self._app_model.has_new_wire():
                self._app_model.new_wire_abort()
                self.update()

    def mouseMoveEvent(self, event):
        """QT event callback function"""
        if self._app_model.is_running:
            return

        if self._app_model.has_new_wire():
            self._app_model.set_new_wire_end_pos(event.pos())
            self.update()

    def dragEnterEvent(self, event):
        """QT event callback function"""
        event.accept()

    def dropEvent(self, event):
        """QT event callback function"""
        event.setDropAction(Qt.IgnoreAction)
        event.accept()
        self.setFocus()

        component_name = event.mimeData().text()
        QTimer.singleShot(0, partial(self.add_component, component_name, event.pos()))

    def add_component(self, name, position):
        """
        Add component to circuit area
        Used be drag'n'drop into Circuit area or double click in SelectableComponentWidget
        """
        if position == QPoint(0, 0):
            position = self.rect().center()

        component_parameters = self._app_model.get_component_parameters(name)
        ok, settings = ComponentSettingsDialog.start(
            self, self._app_model, name, component_parameters
        )
        if ok:
            component_object = self._app_model.add_component_by_name(name, position, settings)
            comp = ComponentWidget(self._app_model, component_object, self)
            comp.show()
            self._app_model.select(component_object)

    def _update_gui_components(self):
        children = self.findChildren(ComponentWidget)
        for child in children:
            child.deleteLater()

        component_objects = self._app_model.get_component_objects()
        for component_object in component_objects:
            comp = ComponentWidget(self._app_model, component_object, self)
            comp.show()
        self._app_model.update_wires()
        self.update()
