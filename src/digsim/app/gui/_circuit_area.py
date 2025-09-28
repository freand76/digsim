# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""The circuit area and component widget"""

from functools import partial

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, Qt, QTimer
from PySide6.QtGui import QBrush, QColor, QPainterPath, QPen
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsPathItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsView,
)

from digsim.app.settings import ComponentSettingsDialog


class WirePartGraphicsItem(QGraphicsRectItem):
    """A part of a wire graphcis item"""

    CLOSE_TO_WIRE_MARGIN = 10

    def __init__(self, app_model, src_port, parent, point_pair):
        src, dst = point_pair
        x_low, x_high = (src.x(), dst.x()) if src.x() < dst.x() else (dst.x(), src.x())
        y_low, y_high = (src.y(), dst.y()) if src.y() < dst.y() else (dst.y(), src.y())
        rect = QRectF(
            x_low - self.CLOSE_TO_WIRE_MARGIN,
            y_low - self.CLOSE_TO_WIRE_MARGIN,
            x_high - x_low + 2 * self.CLOSE_TO_WIRE_MARGIN,
            y_high - y_low + 2 * self.CLOSE_TO_WIRE_MARGIN,
        )
        self._app_model = app_model
        self._src_port = src_port
        self._parent = parent
        self._start = QPointF(x_low, y_low)
        self._end = QPointF(x_high, y_high)
        self._selected = False
        super().__init__(rect, parent)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def wire_selected(self, selected):
        """Set Wire Selected"""
        self._selected = selected

    def itemChange(self, change, value):
        """QT event callback function"""
        if change == QGraphicsItem.ItemSelectedHasChanged:
            self._parent.select(self.isSelected())
        return super().itemChange(change, value)

    def _get_wire_color(self, port_value, bus_width):
        if port_value == "X":
            return Qt.red
        if port_value == 0:
            return Qt.darkGray

        max_value = 2**bus_width - 1
        # Start with dark gray
        green = 128
        # Calculate the green component, ranging from 128 to 255
        green += int(127 * port_value / max_value)
        return QColor(128, green, 128)

    def paint(self, painter, option, widget=None):
        """QT function"""
        pen = QPen(Qt.darkGray)
        bus_width = self._src_port.width
        if bus_width > 1:
            pen.setWidth(4)
        else:
            pen.setWidth(2)

        if not self._app_model.is_running and self._selected:
            pen.setColor(Qt.black)
        elif self._app_model.settings.get("color_wires"):
            port_value = self._src_port.value
            pen.setColor(self._get_wire_color(port_value, bus_width))

        painter.setPen(pen)
        painter.drawLine(self._start, self._end)


class WireGraphicsItem(QGraphicsPathItem):
    """A wire graphics item"""

    WIRE_TO_COMPONENT_DIST = 5
    X_OFFSET = 10

    def __init__(self, app_model, connection, src_port_item, dst_port_item):
        super().__init__()
        self._app_model = app_model
        self._src_port, self._dst_port = connection
        self._src_port_item = src_port_item
        self._dst_port_item = dst_port_item
        self._part_items = []
        self.setZValue(-1)
        self.update_wire()
        self._selected = False

    def disconnect(self):
        """Disconnect (delete) the wire"""
        self._src_port.disconnect(self._dst_port)

    def select(self, selected):
        """Select all parts of the wiregrapgicsitem"""
        for item in self._part_items:
            item.wire_selected(selected)
        if selected:
            self.setZValue(self._app_model.objects.components.get_top_zlevel() + 1)
        else:
            self.setZValue(-1)
        self._selected = selected

    def is_selected(self):
        """Is the wire selected"""
        return self._selected

    @classmethod
    def create_points(cls, source, dest, rect):
        """Create a wire path"""
        points = []
        points.append(source)

        if source.x() < dest.x():
            half_dist_x = (dest.x() - source.x()) / 2
            points.append(QPointF(source.x() + half_dist_x, source.y()))
            points.append(QPointF(source.x() + half_dist_x, dest.y()))
        else:
            half_dist_y = (source.y() + dest.y()) / 2
            if dest.y() < source.y():
                comp_top = rect.y() - cls.WIRE_TO_COMPONENT_DIST
                y_mid = min(comp_top, half_dist_y)
            else:
                comp_bottom = rect.y() + rect.height() + cls.WIRE_TO_COMPONENT_DIST
                y_mid = max(comp_bottom, half_dist_y)

            points.append(QPointF(source.x() + cls.X_OFFSET, source.y()))
            points.append(QPointF(source.x() + cls.X_OFFSET, y_mid))
            points.append(QPointF(dest.x() - cls.X_OFFSET, y_mid))
            points.append(QPointF(dest.x() - cls.X_OFFSET, dest.y()))

        points.append(dest)
        return points

    @classmethod
    def create_path(cls, source, dest, rect):
        """Create a wire path"""
        path = QPainterPath()
        points = cls.create_points(source, dest, rect)
        path.moveTo(points[0])
        for point in points[1:]:
            path.lineTo(point)
        return path

    def update_wire(self):
        """Update the wire path"""
        source = self._src_port_item.portPos()
        dest = self._dst_port_item.portPos()
        rect = self._src_port_item.portParentRect()
        points = self.create_points(source, dest, rect)
        self._part_items = []
        for idx, p1 in enumerate(points[0:-1]):
            p2 = points[idx + 1]
            item = WirePartGraphicsItem(self._app_model, self._src_port, self, (p1, p2))
            self._part_items.append(item)


class NewWireGraphicsItem(QGraphicsPathItem):
    """A new wire graphics item"""

    def __init__(self, app_model):
        super().__init__()
        self._app_model = app_model

    def paint(self, painter, option, widget=None):
        """QT function"""
        end_pos = None
        start_port = self._app_model.objects.new_wire.start_port()
        end_pos = self._app_model.objects.new_wire.end_pos()
        pen = QPen(Qt.darkGray)
        if start_port is None or end_pos is None:
            return
        if start_port.width > 1:
            pen.setWidth(4)
        else:
            pen.setWidth(2)
        component_object = self._app_model.objects.components.get_object(start_port.parent())
        start_pos = component_object.get_port_pos(start_port.name()) + component_object.pos()
        if start_port.is_output():
            path = WireGraphicsItem.create_path(start_pos, end_pos, component_object.rect())
        else:
            path = WireGraphicsItem.create_path(end_pos, start_pos, component_object.rect())
        self.setPath(path)
        self.setPen(pen)
        super().paint(painter, option, widget)


class _CircuitAreaScene(QGraphicsScene):
    """The circuit area graphics scene"""

    def __init__(self, app_model, view):
        super().__init__()
        self._app_model = app_model
        self._view = view
        self._app_model.sig_repaint.connect(self._repaint)
        self._app_model.sig_synchronize_gui.connect(self._synchronize_gui)
        self._app_model.sig_update_wires.connect(self._update_wires)
        self._app_model.sig_delete_component.connect(self._delete_component)
        self._app_model.sig_delete_wires.connect(self._delete_wires)
        self._wire_items = []
        self._select_start_pos = None
        self._selection_rect_item = None
        self._synchronize_gui()

    def _repaint(self):
        self.update()

    def mousePressEvent(self, event):
        """QT event callback function"""
        super().mousePressEvent(event)
        pos = event.scenePos()
        items = self.items(pos)
        if len(items) == 0:
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

        # Make sure to loop through complete list to clear has_moved()
        has_moved_component = False
        for component_object in self._app_model.objects.components.get_object_list():
            if component_object.has_moved():
                has_moved_component = True
        if has_moved_component:
            self._app_model.sig_update_wires.emit()

    def mouseReleaseEvent(self, event):
        """QT event callback function"""
        super().mouseReleaseEvent(event)
        self._select_start_pos = None
        self._selection_rect_item.setVisible(False)
        self._repaint()

    def _delete_component(self, component_object):
        self.removeItem(component_object)
        self._update_wires()

    def _delete_wires(self):
        change = False
        for item in self._wire_items:
            if item.is_selected():
                item.disconnect()
                change = True
        if change:
            self._update_wires()
            self._app_model.model_changed()

    def _update_wires(self):
        for item in self._wire_items:
            self.removeItem(item)

        self._wire_items = []
        component_objects = self._app_model.objects.components.get_object_list()
        for src_comp_item in component_objects:
            for src_port in src_comp_item.component.outports():
                for dst_port in src_port.wired_ports:
                    dst_comp_item = self._app_model.objects.components.get_object(
                        dst_port.parent()
                    )
                    src_port_item = src_comp_item.get_port_item(src_port)
                    dst_port_item = dst_comp_item.get_port_item(dst_port)
                    item = WireGraphicsItem(
                        self._app_model, (src_port, dst_port), src_port_item, dst_port_item
                    )
                    self.addItem(item)
                    self._wire_items.append(item)

    def add_scene_component(self, component_object, update_wires=False):
        """Add component to scene"""
        self.addItem(component_object)
        component_object.set_parent_widget(self._view)
        if update_wires:
            self._update_wires()

    def _synchronize_gui(self):
        """Remove everything from scene"""
        self.clear()
        self._wire_items = []
        # Add new wire item
        self.addItem(NewWireGraphicsItem(self._app_model))
        # Add selection rect
        self._selection_rect_item = QGraphicsRectItem()
        self._selection_rect_item.setPen(Qt.DashLine)
        self._selection_rect_item.setBrush(Qt.Dense7Pattern)
        self.addItem(self._selection_rect_item)
        # Add component
        for component_object in self._app_model.objects.components.get_object_list():
            self.add_scene_component(component_object)
        # Update (add) wires
        self._update_wires()


class CircuitArea(QGraphicsView):
    """The circuit area graphics view"""

    ZOOM_IN_FACTOR = 1.25
    ZOOM_OUT_FACTOR = 0.8

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
        self._mouse_pos = QPoint(0, 0)

    def has_selection(self):
        """Return true if items are selected"""
        return len(self._scene.selectedItems()) > 0

    def _zoom_in(self):
        self.scale(self.ZOOM_IN_FACTOR, self.ZOOM_IN_FACTOR)

    def _zoom_out(self):
        self.scale(self.ZOOM_OUT_FACTOR, self.ZOOM_OUT_FACTOR)

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
        self._mouse_pos = event.pos()
        # Draw unfinished wire
        if self._app_model.objects.new_wire.ongoing():
            scene_pos = self.mapToScene(event.pos())
            self._app_model.objects.new_wire.set_end_pos(scene_pos)
            self._repaint()

    def wheelEvent(self, event):
        """QT event callback function"""
        # Zoom on wheel
        if not self._wheel_zoom_mode:
            super().wheelEvent(event)
            return
        if event.angleDelta().y() > 0:
            before = self.mapToScene(self._mouse_pos)
            self._zoom_in()
            after = self.mapToScene(self._mouse_pos)
            translation = after - before
            self.translate(translation.x(), translation.y())
        elif event.angleDelta().y() < 0:
            before = self.mapToScene(self._mouse_pos)
            self._zoom_out()
            after = self.mapToScene(self._mouse_pos)
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
            self._scene.add_scene_component(component_object, True)
