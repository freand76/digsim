# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

"""The circuit area and component widget"""

# pylint: disable=unused-argument
# pylint: disable=useless-parent-delegation
# pylint: disable=too-few-public-methods

from functools import partial

from PySide6.QtCore import QPoint, QRect, Qt, QTimer
from PySide6.QtGui import QAction, QBrush, QPainterPath, QPen
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsPathItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsView,
    QMenu,
)

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


class WireGraphicsItem(QGraphicsPathItem):
    """A wire graphics item"""

    WIRE_TO_COMPONENT_DIST = 5

    def __init__(self, app_model, wire_object, src_port_item, dst_port_item):
        super().__init__()
        self._app_model = app_model
        self._wire_object = wire_object
        self._src_port_item = src_port_item
        self._dst_port_item = dst_port_item
        self.update_wire(0)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)

    def _repaint(self):
        """Make scene repaint for component update"""
        self._app_model.sig_repaint.emit()

    def setSelected(self, selected):
        """Qt function"""
        self._wire_object.select(selected)
        self._app_model.sig_control_notify.emit()
        super().setSelected(selected)

    def itemChange(self, change, value):
        """QT event callback function"""
        if change == QGraphicsItem.ItemSelectedHasChanged:
            self._app_model.sig_control_notify.emit()
            self._wire_object.select(self.isSelected())
            self._repaint()
        return super().itemChange(change, value)

    @classmethod
    def create_path(cls, source, dest, rect):
        """Create a wire path"""
        component_top_y = rect.y()
        component_bottom_y = rect.y() + rect.height()

        path = QPainterPath()
        path.moveTo(source)
        if source.x() < dest.x():
            half_dist_x = (dest.x() - source.x()) / 2
            path.lineTo(QPoint(source.x() + half_dist_x, source.y()))
            path.lineTo(QPoint(source.x() + half_dist_x, source.y()))
            path.lineTo(QPoint(source.x() + half_dist_x, dest.y()))
        else:
            half_dist_y = (dest.y() - source.y()) / 2
            if dest.y() < source.y():
                y_mid = max(
                    component_bottom_y - source.y() + cls.WIRE_TO_COMPONENT_DIST, half_dist_y
                )
            else:
                y_mid = min(component_top_y - source.y() - cls.WIRE_TO_COMPONENT_DIST, half_dist_y)
            path.lineTo(QPoint(source.x() + 10, source.y()))
            path.lineTo(QPoint(source.x() + 10, source.y() + y_mid))
            path.lineTo(QPoint(dest.x() - 10, source.y() + y_mid))
            path.lineTo(QPoint(dest.x() - 10, dest.y()))
        path.lineTo(dest)
        return path

    def paint(self, painter, option, widget=None):
        """QT function"""
        pen = QPen(Qt.black)
        bus_width = self._wire_object.src_port.width
        if bus_width > 1:
            pen.setWidth(4)
        else:
            pen.setWidth(2)
        if self._app_model.is_running or not self.isSelected():
            pen.setColor(Qt.darkGray)
            port_value = self._wire_object.src_port.value
            color_wires = self._app_model.settings.get("color_wires")
            if color_wires and port_value != 0 and port_value != "X":
                max_value = 2**bus_width - 1
                color = pen.color()
                green = color.green()
                full_range = 255 - green
                color.setGreen(green + (full_range * port_value / max_value))
                pen.setColor(color)
        painter.setPen(pen)
        painter.drawPath(self.path())
        # super().paint(painter, option, widget)

    def update_wire(self, zvalue):
        """Update the wire path"""
        source = self._src_port_item.portPos()
        dest = self._dst_port_item.portPos()
        rect = self._src_port_item.portParentRect()
        self.setZValue(zvalue)
        self.setPath(self.create_path(source, dest, rect))


class NewWireGraphicsItem(QGraphicsPathItem):
    """A new wire graphics item"""

    def __init__(self, app_model):
        super().__init__()
        self._app_model = app_model

    def paint(self, painter, option, widget=None):
        """QT function"""
        end_pos = None
        wire_object = self._app_model.objects.wires.new.wire
        end_pos = self._app_model.objects.wires.new.end_pos
        pen = QPen(Qt.darkGray)
        if wire_object is None or end_pos is None:
            return
        start_port = wire_object.dst_port if wire_object.src_port is None else wire_object.src_port
        if start_port.width > 1:
            pen.setWidth(4)
        else:
            pen.setWidth(2)
        component_object = self._app_model.objects.components.get_object(start_port.parent())
        start_pos = component_object.get_port_pos(start_port.name())
        if wire_object.src_port is not None:
            path = WireGraphicsItem.create_path(start_pos, end_pos, component_object.get_rect())
        else:
            path = WireGraphicsItem.create_path(end_pos, start_pos, component_object.get_rect())
        self.setPath(path)
        self.setPen(pen)
        super().paint(painter, option, widget)


class PortGraphicsItem(QGraphicsRectItem):
    """A port graphics item"""

    def __init__(self, app_model, parent, port, rect):
        super().__init__(rect, parent)
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
        if self._app_model.objects.wires.new.ongoing():
            try:
                self._app_model.objects.wires.new.end(self._port.parent(), self._port.name())
            except PortConnectionError as exc:
                self._app_model.objects.wires.new.abort()
                self._app_model.sig_error.emit(str(exc))
                self._repaint()
        else:
            self._app_model.objects.wires.new.start(self._port.parent(), self._port.name())

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

    def __init__(self, parent, app_model, component_object):
        super().__init__(QRect(component_object.pos, component_object.size))
        self._parent = parent
        self._app_model = app_model
        self._component_object = component_object
        self._component = self._component_object.component
        self._wire_items = []
        self._port_dict = {}
        self._mouse_press_pos = None
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)
        for portname, port_rect in self._component_object._port_rects.items():
            port = self._component_object.component.port(portname)
            item = PortGraphicsItem(app_model, self, port, port_rect)
            self._port_dict[port] = item

    @property
    def component(self):
        """Get component from widget"""
        return self._component_object.component

    def sync_from_gui(self):
        """Get component from widget"""
        new_pos = self.pos() + self.rect().topLeft()
        self._component_object.pos = new_pos.toPoint()

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
        self._app_model.sig_control_notify.emit()
        self._component_object.select(selected)
        super().setSelected(selected)

    def itemChange(self, change, value):
        """QT event callback function"""
        if change == QGraphicsItem.ItemPositionHasChanged:
            for wire_item in self._wire_items:
                wire_item.update_wire(self.zValue())
        elif change == QGraphicsItem.ItemSelectedHasChanged:
            self._app_model.sig_control_notify.emit()
            self._component_object.select(self.isSelected())
            self._repaint()
        return super().itemChange(change, value)

    def paint(self, painter, option, widget=None):
        """QT function"""
        self.setZValue(self._component_object.zlevel)
        self._component_object.paint_component(painter)
        self._component_object.paint_ports(painter)

    def hoverEnterEvent(self, _):
        """QT event callback function"""
        if self._app_model.is_running and self.component.has_action:
            self.setCursor(Qt.PointingHandCursor)

    def hoverLeaveEvent(self, _):
        """QT event callback function"""
        self.setCursor(Qt.ArrowCursor)

    def mouseMoveEvent(self, event):
        """QT event callback function"""
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        """QT event callback function"""
        super().mousePressEvent(event)
        if event.button() == Qt.LeftButton:
            if self._app_model.is_running:
                self._app_model.model_add_event(self.component.onpress)
            else:
                self._mouse_press_pos = event.screenPos()
                self.setCursor(Qt.ClosedHandCursor)
                self._repaint()

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
                    self._app_model.model_changed()
                else:
                    if not self._app_model.objects.wires.new.ongoing():
                        self._component_object.single_click_action()
        self._mouse_press_pos = None

    def contextMenuEvent(self, event):
        """Create conext menu for component"""
        if self._app_model.is_running:
            return
        if self._app_model.objects.wires.new.ongoing():
            self._app_model.objects.wires.new.abort()
        context_menu = ComponentContextMenu(self._parent, self._app_model, self._component_object)
        context_menu.create(event.screenPos())


class _CircuitAreaScene(QGraphicsScene):
    """The circuit area graphics scene"""

    def __init__(self, app_model, view):
        super().__init__()
        self._app_model = app_model
        self._view = view
        self._app_model.sig_repaint.connect(self._repaint)
        self._app_model.sig_synchronize_gui.connect(self._synchronize_gui)
        self._component_items = {}
        self._select_start_pos = None
        self._selection_rect_item = None

    def _repaint(self):
        self.update()

    def _selectNone(self):
        for item in self.items():
            item.setSelected(False)

    def mousePressEvent(self, event):
        """QT event callback function"""
        super().mousePressEvent(event)
        pos = event.scenePos()
        items = self.items(pos)
        if len(items) == 0:
            self._selectNone()
            self._select_start_pos = pos
        self._repaint()

    def mouseMoveEvent(self, event):
        """QT event callback function"""
        super().mouseMoveEvent(event)
        pos = event.scenePos()
        if self._select_start_pos is not None:
            path = QPainterPath()
            rect = QRect(
                self._select_start_pos.x(),
                self._select_start_pos.y(),
                pos.x() - self._select_start_pos.x(),
                pos.y() - self._select_start_pos.y(),
            )
            self._selection_rect_item.setRect(rect)
            self._selection_rect_item.setVisible(True)
            path.addRect(rect)
            self.setSelectionArea(path)
            self._repaint()

    def mouseReleaseEvent(self, event):
        """QT event callback function"""
        super().mouseReleaseEvent(event)
        self._select_start_pos = None
        self._selection_rect_item.setVisible(False)
        self._repaint()

    def remove_all(self):
        """Remove everything from scene"""
        self.clear()
        self.addItem(NewWireGraphicsItem(self._app_model))
        self._selection_rect_item = QGraphicsRectItem()
        self._selection_rect_item.setPen(Qt.DashLine)
        self._selection_rect_item.setBrush(Qt.Dense7Pattern)
        self.addItem(self._selection_rect_item)

    def _synchronize_gui(self):
        for _, item in self._component_items.items():
            item.sync_from_gui()

        self.remove_all()
        self._component_items = {}
        component_objects = self._app_model.objects.components.get_object_list()
        for component_object in component_objects:
            item = ComponentGraphicsItem(self._view, self._app_model, component_object)
            self.addItem(item)
            self._component_items[component_object.component] = item
        wire_objects = self._app_model.objects.wires.get_object_list()
        for wire_object in wire_objects:
            src_comp = wire_object.src_port.parent()
            dst_comp = wire_object.dst_port.parent()
            src_comp_item = self._component_items[src_comp]
            dst_comp_item = self._component_items[dst_comp]
            src_port_item = src_comp_item.get_port_item(wire_object.src_port)
            dst_port_item = dst_comp_item.get_port_item(wire_object.dst_port)
            item = WireGraphicsItem(self._app_model, wire_object, src_port_item, dst_port_item)
            self.addItem(item)
            src_comp_item.add_wire(item)
            dst_comp_item.add_wire(item)


class CircuitArea(QGraphicsView):
    """The circuit area graphics view"""

    def __init__(self, app_model, parent):
        super().__init__(parent=parent)
        self._app_model = app_model
        self._app_model.sig_zoom_in_gui.connect(self._zoom_in)
        self._app_model.sig_zoom_out_gui.connect(self._zoom_out)
        self._scene = _CircuitAreaScene(app_model, self)
        self._wheel_zoom_mode = False
        self.setScene(self._scene)
        self.setBackgroundBrush(QBrush(Qt.lightGray))
        self.setAcceptDrops(True)
        self.setTransformationAnchor(QGraphicsView.NoAnchor)

    def has_selection(self):
        """Return true if items are selected"""
        return len(self._scene.selectedItems()) > 0

    def _zoom_in(self):
        self.scale(1.25, 1.25)

    def _zoom_out(self):
        self.scale(0.8, 0.8)

    def _repaint(self):
        """Make scene repaint for component update"""
        self._app_model.sig_repaint.emit()

    def keyPressEvent(self, event):
        """QT event callback function"""
        super().keyPressEvent(event)
        if event.isAutoRepeat():
            return
        if event.key() == Qt.Key_Shift:
            self.setCursor(Qt.OpenHandCursor)
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            event.accept()
        elif event.key() == Qt.Key_Control:
            self.setCursor(Qt.ArrowCursor)
            self._wheel_zoom_mode = True
            event.accept()

    def keyReleaseEvent(self, event):
        """QT event callback function"""
        super().keyReleaseEvent(event)
        if event.isAutoRepeat():
            return
        if event.key() == Qt.Key_Shift:
            self.setCursor(Qt.ArrowCursor)
            self.setDragMode(QGraphicsView.NoDrag)
            event.accept()
        elif event.key() == Qt.Key_Control:
            self.setCursor(Qt.ArrowCursor)
            self._wheel_zoom_mode = False
            event.accept()

    def dragEnterEvent(self, event):
        """QT event callback function"""
        event.accept()

    def dragLeaveEvent(self, event):
        """QT event callback function"""
        event.accept()

    def dragMoveEvent(self, event):
        """QT event callback function"""
        event.accept()

    def dropEvent(self, event):
        """QT event callback function"""
        event.setDropAction(Qt.IgnoreAction)
        event.accept()
        self.setFocus()

        scene_pos = self.mapToScene(event.pos())

        component_name = event.mimeData().text()
        QTimer.singleShot(0, partial(self.add_component, component_name, scene_pos))

    def enterEvent(self, event):
        """QT event callback function"""
        self.setFocus()
        event.accept()

    def mousePressEvent(self, event):
        """QT event callback function"""
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """QT event callback function"""
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        """QT event callback function"""
        super().mouseMoveEvent(event)
        # Draw unfinished wire
        if self._app_model.objects.wires.new.ongoing():
            scene_pos = self.mapToScene(event.pos())
            self._app_model.objects.wires.new.set_end_pos(scene_pos)
            self._repaint()

    def wheelEvent(self, event):
        """QT event callback function"""
        # Zoom on wheel
        if not self._wheel_zoom_mode:
            super().wheelEvent(event)
            return
        if event.angleDelta().y() > 0:
            before = self.mapToScene(event.pos())
            self._zoom_in()
            after = self.mapToScene(event.pos())
            translation = after - before
            self.translate(translation.x(), translation.y())
        elif event.angleDelta().y() < 0:
            before = self.mapToScene(event.pos())
            self._zoom_out()
            after = self.mapToScene(event.pos())
            translation = after - before
            self.translate(translation.x(), translation.y())
        event.accept()

    def add_component(self, name, position):
        """
        Add component to circuit area
        Used be drag'n'drop into Circuit area or double click in SelectableComponentWidget
        """
        if position is None:
            position = self.mapToScene(0, 0) + QPoint(100, 100)

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
            component_object.select(True)
