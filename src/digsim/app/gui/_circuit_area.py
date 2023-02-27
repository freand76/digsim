# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

"""The circuit area and component widget"""

from functools import partial

from PySide6.QtCore import QPoint, QRect, Qt, QTimer
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QPushButton, QScrollArea, QWidget

from digsim.app.settings import ComponentSettingsDialog
from digsim.circuit.components.atoms import PortConnectionError


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

    def app_model(self):
        """Get app_model from widget"""
        return self._app_model

    def sizeHint(self):
        """QT event callback function"""
        return self._component_object.size

    @property
    def component(self):
        """Get component from widget"""
        return self._component_object.component

    def _component_notify(self, component):
        if component == self.component:
            self.move(self._component_object.pos)
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
                self._component_object.create_context_menu(self, self.mapToGlobal(event.pos()))
                self._component_object.update_size()
                self._app_model.sig_update_gui_components.emit()
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
            self._app_model.move_selected_components(event.pos() - self._mouse_grab_pos)
            self.parent().update()


class CircuitArea(QWidget):
    """The circuit area class, this is where the component widgets are placed"""

    def __init__(self, app_model, parent):
        super().__init__(parent)
        self.setFixedWidth(5000)
        self.setFixedHeight(5000)
        self._app_model = app_model
        self._app_model.sig_update_gui_components.connect(self._update_gui_components)
        self._select_box_start = None
        self._select_box_rect = None
        self.setMouseTracking(True)
        self.setAcceptDrops(True)
        self._panning_mode = False
        self._panning_pos = None
        self._panning_callback = None
        self._top_left = QPoint(0, 0)

    def set_top_left(self, point):
        """Set top left position for visible circuit area"""
        self._top_left = point

    def set_panning_callback(self, callback):
        """Set callback funktion to handle panning of parent scroll area"""
        self._panning_callback = callback

    def _abort_wire(self):
        self._app_model.new_wire_abort()
        self.update()

    def keyPressEvent(self, event):
        """QT event callback function"""
        super().keyPressEvent(event)
        if self._app_model.is_running:
            return
        if event.key() == Qt.Key_Delete:
            self._app_model.delete()
        elif event.key() == Qt.Key_Escape:
            if self._app_model.has_new_wire():
                self._abort_wire()
        elif event.key() == Qt.Key_Control:
            self._app_model.multi_select(True)
        elif event.key() == Qt.Key_Shift:
            self.setCursor(Qt.OpenHandCursor)
            self._panning_mode = True
        event.accept()

    def keyReleaseEvent(self, event):
        """QT event callback function"""
        super().keyReleaseEvent(event)
        if self._app_model.is_running:
            return
        if event.key() == Qt.Key_Control:
            self._app_model.multi_select(False)
        elif event.key() == Qt.Key_Shift:
            self.setCursor(Qt.ArrowCursor)
            self._panning_mode = False

    def paintEvent(self, _):
        """QT event callback function"""
        painter = QPainter(self)
        self._app_model.paint_wires(painter)
        if self._select_box_rect is not None:
            painter.setBrush(Qt.Dense7Pattern)
            painter.drawRect(self._select_box_rect)
            self._app_model.select_by_rect(self._select_box_rect)
        painter.end()

    def mousePressEvent(self, event):
        """QT event callback function"""
        super().mousePressEvent(event)
        self.setFocus()
        if event.button() == Qt.LeftButton:
            if self._app_model.is_running:
                return
            if self._app_model.has_new_wire():
                return
            if self._app_model.select_by_position(event.pos()):
                self.update()
                return
            if self._panning_mode:
                self._panning_pos = event.pos()
            else:
                self._select_box_start = event.pos()
                self.update()
        elif event.button() == Qt.RightButton:
            if self._app_model.is_running:
                return
            if self._app_model.has_new_wire():
                self._abort_wire()

    def _end_selection(self):
        if self._select_box_rect is not None:
            self._app_model.select_by_rect(self._select_box_rect)
        self._select_box_start = None
        self._select_box_rect = None

    def mouseReleaseEvent(self, event):
        """QT event callback function"""
        super().mouseReleaseEvent(event)
        if event.button() == Qt.LeftButton:
            if self._app_model.is_running:
                return
            self._panning_pos = None
            self._end_selection()
            self.update()

    def mouseDoubleClickEvent(self, _):
        """QT event callback function"""
        if self._app_model.is_running:
            return
        if self._app_model.has_new_wire():
            self._abort_wire()

    def mouseMoveEvent(self, event):
        """QT event callback function"""
        if self._app_model.is_running:
            return

        if self._app_model.has_new_wire():
            self._app_model.set_new_wire_end_pos(event.pos())
            self.update()
            return

        if self._select_box_start is not None:
            self._select_box_rect = QRect(self._select_box_start, event.pos())
            self.update()
            return

        if (
            self._panning_mode
            and self._panning_pos is not None
            and self._panning_callback is not None
        ):
            self._panning_callback(self._panning_pos - event.pos())

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
        if position is None:
            position = self._top_left + QPoint(100, 100)

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


class ScrollableCircuitArea(QScrollArea):
    """The scrollable circuit area class, this is where the circuit area widgets is placed"""

    def __init__(self, parent, circuit_area):
        super().__init__(parent)
        self._circuit_area = circuit_area
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setWidget(circuit_area)
        self._circuit_area.set_panning_callback(self.panning_callback)

    def scrollContentsBy(self, dx, dy):
        """QT event callback function"""
        super().scrollContentsBy(dx, dy)
        self._circuit_area.set_top_left(
            QPoint(self.horizontalScrollBar().value(), self.verticalScrollBar().value())
        )

    def panning_callback(self, delta):
        """Pan the scroll area by the delta position"""
        self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() + delta.x())
        self.verticalScrollBar().setValue(self.verticalScrollBar().value() + delta.y())
