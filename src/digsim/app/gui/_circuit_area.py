# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

"""The circuit area and component widget"""

from functools import partial

from PySide6.QtCore import QPoint, QRect, Qt, QTimer
from PySide6.QtGui import QAction, QPainter
from PySide6.QtWidgets import QMenu, QPushButton, QScrollArea, QWidget

from digsim.app.settings import ComponentSettingsDialog
from digsim.circuit.components.atoms import PortConnectionError


class ComponentContextMenu(QMenu):
    """The component contextmenu class"""

    def __init__(self, parent, app_model, component_object):
        super().__init__(parent)
        self._parent = parent
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
        self._app_model.objects.select(self._component_object)
        self._app_model.objects.delete_selected()

    def _raise(self):
        self._parent.raise_()

    def _lower(self):
        self._parent.lower()

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


class ComponentWidget(QPushButton):
    """A component widget, a 'clickable' widget with a custom paintEvent"""

    def __init__(self, app_model, component_object, parent):
        super().__init__(parent, objectName=component_object.component.name())
        self._app_model = app_model
        self._app_model.sig_component_notify.connect(self._component_notify)
        self._component_object = component_object
        self._move_start_pos = None
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
            self._app_model.objects.wires.new.end(self.component, self._active_port)
        except PortConnectionError as exc:
            self._app_model.objects.wires.new.abort()
            self._app_model.sig_error.emit(str(exc))
            self.parent().update()

    def mousePressEvent(self, event):
        """QT event callback function"""
        super().mousePressEvent(event)
        if event.button() == Qt.LeftButton:
            if self._app_model.is_running:
                self._app_model.model_add_event(self.component.onpress)
            elif self._app_model.objects.wires.new.ongoing():
                if self._active_port is not None:
                    self._new_wire_end()
            else:
                self._app_model.objects.select(self._component_object)
                if self._active_port is None:
                    # Prepare to move
                    self.setCursor(Qt.ClosedHandCursor)
                    self._move_start_pos = event.pos()
                else:
                    self._app_model.objects.wires.new.start(self.component, self._active_port)
        elif event.button() == Qt.RightButton:
            if self._app_model.is_running:
                return
            if self._app_model.objects.wires.new.ongoing():
                self._app_model.objects.wires.new.abort()
            else:
                contect_menu = ComponentContextMenu(self, self._app_model, self._component_object)
                contect_menu.create(self.mapToGlobal(event.pos()))
        self.update()

    def mouseReleaseEvent(self, event):
        """QT event callback function"""
        super().mouseReleaseEvent(event)
        if event.button() == Qt.LeftButton:
            if self._app_model.is_running:
                self._app_model.model_add_event(self.component.onrelease)
                return

            # Move complete?
            self.setCursor(Qt.ArrowCursor)
            has_movement = False
            if self._move_start_pos is not None:
                has_movement = self._app_model.objects.move_selected_components(
                    event.pos() - self._move_start_pos,
                    finalize=True,
                )
                self._move_start_pos = None
            if not has_movement and not self._app_model.objects.wires.new.ongoing():
                self._component_object.single_click_action()

    def mouseMoveEvent(self, event):
        """QT event callback function"""
        self._component_object.mouse_position(event.pos())

        if self._app_model.is_running:
            return

        if self._app_model.objects.multi_select_ongoing():
            return

        active_port = self._component_object.get_port_for_point(event.pos())
        if active_port != self._active_port:
            self._active_port = active_port
            if self._active_port is not None:
                self.setCursor(Qt.CrossCursor)
            else:
                self.setCursor(Qt.ArrowCursor)
            self.update()

        if self._app_model.objects.wires.new.ongoing():
            end_pos = event.pos()
            if self._active_port:
                end_pos = self._component_object.get_port_pos(self._active_port)
            self._app_model.objects.wires.new.set_end_pos(self.pos() + end_pos)
            self.parent().update()

        elif self._move_start_pos is not None:
            self._app_model.objects.move_selected_components(event.pos() - self._move_start_pos)
            self.parent().update()


class CircuitArea(QWidget):
    """The circuit area class, this is where the component widgets are placed"""

    def __init__(self, app_model, parent):
        super().__init__(parent)
        self.setFixedWidth(5000)
        self.setFixedHeight(5000)
        self._app_model = app_model
        self._app_model.sig_synchronize_gui.connect(self._synchronize_gui)
        self._app_model.sig_repaint_wires.connect(self._repaint)
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
        self._app_model.objects.wires.new.abort()
        self.update()

    def _repaint(self):
        self.repaint()

    def keyPressEvent(self, event):
        """QT event callback function"""
        super().keyPressEvent(event)
        if event.isAutoRepeat():
            return
        if self._app_model.is_running:
            return
        if event.key() == Qt.Key_Shift:
            self.setCursor(Qt.OpenHandCursor)
            self._panning_mode = True
            event.accept()

    def keyReleaseEvent(self, event):
        """QT event callback function"""
        super().keyReleaseEvent(event)
        if event.isAutoRepeat():
            return
        if self._app_model.is_running:
            return
        if event.key() == Qt.Key_Shift:
            self.setCursor(Qt.ArrowCursor)
            self._panning_mode = False
            event.accept()

    def paintEvent(self, _):
        """QT event callback function"""
        painter = QPainter(self)
        self._app_model.objects.wires.paint(painter)
        if self._select_box_rect is not None:
            painter.setBrush(Qt.Dense7Pattern)
            painter.drawRect(self._select_box_rect)
            self._app_model.objects.select_by_rect(self._select_box_rect)
        painter.end()

    def mousePressEvent(self, event):
        """QT event callback function"""
        super().mousePressEvent(event)
        self.setFocus()
        if event.button() == Qt.LeftButton:
            if self._app_model.is_running:
                return
            if self._app_model.objects.wires.new.ongoing():
                return
            if self._app_model.objects.select_by_position(event.pos()):
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
            if self._app_model.objects.wires.new.ongoing():
                self._abort_wire()

    def _end_selection(self):
        if self._select_box_rect is not None:
            self._app_model.objects.select_by_rect(self._select_box_rect)
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
        if self._app_model.objects.wires.new.ongoing():
            self._abort_wire()

    def mouseMoveEvent(self, event):
        """QT event callback function"""
        if self._app_model.is_running:
            return

        if self._app_model.objects.wires.new.ongoing():
            self._app_model.objects.wires.new.set_end_pos(event.pos())
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

        component_parameters = self._app_model.objects.components.get_object_parameters(name)
        ok, settings = ComponentSettingsDialog.start(
            self, self._app_model, name, component_parameters
        )
        if settings.get("name") is not None:
            name = settings["name"]
        if ok:
            component_object = self._app_model.objects.components.add_object_by_name(
                name, position, settings
            )
            comp = ComponentWidget(self._app_model, component_object, self)
            comp.show()
            self._app_model.objects.select(component_object)

    def _synchronize_gui(self):
        children = self.findChildren(ComponentWidget)
        for child in children:
            child.deleteLater()

        component_objects = self._app_model.objects.components.get_object_list()
        for component_object in component_objects:
            comp = ComponentWidget(self._app_model, component_object, self)
            comp.show()
        self._app_model.objects.wires.update()
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
