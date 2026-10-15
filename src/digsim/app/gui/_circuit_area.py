# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""The circuit area and component widget"""

from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QEvent, QPoint, QPointF, QRect, QRectF, Qt, QTimer
from PySide6.QtGui import (
    QBrush,
    QColor,
    QDragEnterEvent,
    QDragLeaveEvent,
    QDragMoveEvent,
    QDropEvent,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPen,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsPathItem,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSceneMouseEvent,
    QGraphicsView,
    QStyleOptionGraphicsItem,
    QWidget,
)

from digsim.app.gui_objects import ComponentObject
from digsim.app.gui_objects._buzzer_object import BuzzerObject
from digsim.app.gui_objects._component_port_item import PortGraphicsItem
from digsim.app.settings import ComponentSettingsDialog
from digsim.circuit.components.atoms import VALUE_TYPE, Component, Port

from ._drag_preview import drag_preview


if TYPE_CHECKING:
    from digsim.app.model import AppModel


class WirePartGraphicsItem(QGraphicsRectItem):
    """A part of a wire graphics item"""

    CLOSE_TO_WIRE_MARGIN = 10

    def __init__(
        self,
        app_model: AppModel,
        src_port: Port,
        parent: WireGraphicsItem,
        point_pair: tuple[QPointF, QPointF],
    ) -> None:
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
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)

    def wire_selected(self, selected: bool) -> None:
        """Set Wire Selected"""
        self._selected = selected

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value: Any) -> Any:
        """QT event callback function"""
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedChange:
            # Like components, wires can't be selected while the simulation runs
            if self._app_model.is_running:
                value = False
        elif change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            self._parent.select(self.isSelected())
        return super().itemChange(change, value)

    def _get_wire_color(self, port_value: VALUE_TYPE, bus_width: int) -> QColor | Qt.GlobalColor:
        if port_value == "X":
            return Qt.GlobalColor.red
        if port_value == 0:
            return Qt.GlobalColor.darkGray
        assert isinstance(port_value, int)

        max_value = 2**bus_width - 1
        # Start with dark gray
        green = 128
        # Calculate the green component, ranging from 128 to 255
        green += int(127 * port_value / max_value)
        return QColor(128, green, 128)

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        """QT function"""
        pen = QPen(Qt.GlobalColor.darkGray)
        bus_width = self._src_port.width
        if bus_width > 1:
            pen.setWidth(4)
        else:
            pen.setWidth(2)

        if not self._app_model.is_running and self._selected:
            pen.setColor(Qt.GlobalColor.black)
        elif self._app_model.settings.get("color_wires"):
            port_value = self._src_port.value
            pen.setColor(self._get_wire_color(port_value, bus_width))

        painter.setPen(pen)
        painter.drawLine(self._start, self._end)


class WireGraphicsItem(QGraphicsPathItem):
    """A wire graphics item"""

    WIRE_TO_COMPONENT_DIST = 5
    X_OFFSET = 10

    def __init__(
        self,
        app_model: AppModel,
        connection: tuple[Port, Port],
        src_port_item: PortGraphicsItem,
        dst_port_item: PortGraphicsItem,
    ) -> None:
        super().__init__()
        self._app_model = app_model
        self._src_port, self._dst_port = connection
        self._src_port_item = src_port_item
        self._dst_port_item = dst_port_item
        self._part_items: list[WirePartGraphicsItem] = []
        self.setZValue(-1)
        self.update_wire()
        self._selected = False

    def disconnect(self) -> None:
        """Disconnect (delete) the wire"""
        self._src_port.disconnect(self._dst_port)

    def select(self, selected: bool) -> None:
        """Select all parts of the wire"""
        for item in self._part_items:
            item.wire_selected(selected)
        if selected:
            self.setZValue(self._app_model.objects.components.get_top_zlevel() + 1)
        else:
            self.setZValue(-1)
        self._selected = selected

    def is_selected(self) -> bool:
        """Is the wire selected"""
        return self._selected

    @classmethod
    def create_points(cls, source: QPointF, dest: QPointF, rect: QRectF) -> list[QPointF]:
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
    def create_path(cls, source: QPointF, dest: QPointF, rect: QRectF) -> QPainterPath:
        """Create a wire path"""
        path = QPainterPath()
        points = cls.create_points(source, dest, rect)
        path.moveTo(points[0])
        for point in points[1:]:
            path.lineTo(point)
        return path

    def update_wire(self) -> None:
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

    def __init__(self, app_model: AppModel) -> None:
        super().__init__()
        self._app_model = app_model

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        """QT function"""
        start_port = self._app_model.objects.new_wire.start_port()
        end_pos = self._app_model.objects.new_wire.end_pos()
        pen = QPen(Qt.GlobalColor.darkGray)
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

    _selection_rect_item: QGraphicsRectItem

    def __init__(self, app_model: AppModel, view: CircuitArea) -> None:
        super().__init__()
        self._app_model = app_model
        self._view = view
        self._app_model.sig_repaint.connect(self._repaint)
        self._app_model.sig_synchronize_gui.connect(self._synchronize_gui)
        self._app_model.sig_update_wires.connect(self._update_wires)
        self._app_model.sig_delete_component.connect(self._delete_component)
        self._app_model.sig_delete_wires.connect(self._delete_wires)
        # Forwarded to the current GUI objects, see ComponentObject.disconnect()
        self._app_model.sig_control_notify.connect(self._control_notify)
        self._app_model.sig_audio_start.connect(self._audio_start)
        self._app_model.sig_audio_notify.connect(self._audio_notify)
        self._wire_items: list[WireGraphicsItem] = []
        self._select_start_pos: QPointF | None = None
        self._synchronize_gui()

    def _repaint(self) -> None:
        self.update()

    def _control_notify(self) -> None:
        for component_object in self._app_model.objects.get_list():
            component_object.control_notify()

    def _audio_start(self, enable: bool) -> None:
        for component_object in self._app_model.objects.get_list():
            if isinstance(component_object, BuzzerObject):
                component_object.audio_start(enable)

    def _audio_notify(self, component: Component) -> None:
        # The component may already be gone, if the circuit changed after the signal was sent
        component_object = self._app_model.objects.components.get_dict().get(component)
        if isinstance(component_object, BuzzerObject):
            component_object.audio_notify()

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """QT event callback function"""
        super().mousePressEvent(event)
        pos = event.scenePos()
        items = self.items(pos)
        if len(items) == 0:
            self._select_start_pos = pos
        self._repaint()

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """QT event callback function"""
        super().mouseMoveEvent(event)
        pos = event.scenePos()
        if self._select_start_pos is not None:
            path = QPainterPath()
            rect = QRect(
                int(self._select_start_pos.x()),
                int(self._select_start_pos.y()),
                int(pos.x() - self._select_start_pos.x()),
                int(pos.y() - self._select_start_pos.y()),
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

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """QT event callback function"""
        super().mouseReleaseEvent(event)
        self._select_start_pos = None
        self._selection_rect_item.setVisible(False)
        # Components may have been moved outside the scene
        self._view.grow_scene_rect()
        self._repaint()

    def _delete_component(self, component_object: ComponentObject) -> None:
        self.removeItem(component_object)
        self._update_wires()

    def _delete_wires(self) -> None:
        change = False
        for item in self._wire_items:
            if item.is_selected():
                item.disconnect()
                change = True
        if change:
            self._update_wires()
            self._app_model.model_changed()

    def _update_wires(self) -> None:
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

    def add_scene_component(
        self, component_object: ComponentObject, update_wires: bool = False
    ) -> None:
        """Add component to scene"""
        self.addItem(component_object)
        component_object.set_parent_widget(self._view)
        if update_wires:
            self._update_wires()

    def _synchronize_gui(self) -> None:
        """Remove everything from scene"""
        self.clear()
        # Let the scene size follow the new circuit
        self.setSceneRect(QRectF())
        self._wire_items = []
        # Add new wire item
        self.addItem(NewWireGraphicsItem(self._app_model))
        # Add selection rect
        self._selection_rect_item = QGraphicsRectItem()
        self._selection_rect_item.setPen(Qt.PenStyle.DashLine)
        self._selection_rect_item.setBrush(Qt.BrushStyle.Dense7Pattern)
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

    def __init__(self, app_model: AppModel, parent: QWidget) -> None:
        super().__init__(parent=parent)
        self._app_model = app_model
        self._app_model.sig_zoom_in_gui.connect(self._zoom_in)
        self._app_model.sig_zoom_out_gui.connect(self._zoom_out)
        self._scene = _CircuitAreaScene(app_model, self)
        self._wheel_zoom_mode = False
        self.setScene(self._scene)
        self.setBackgroundBrush(QBrush(Qt.GlobalColor.lightGray))
        self.setAcceptDrops(True)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.NoAnchor)
        self._mouse_pos = QPoint(0, 0)
        self._drag_preview: QGraphicsPixmapItem | None = None

    def has_selection(self) -> bool:
        """Return true if items are selected"""
        return len(self._scene.selectedItems()) > 0

    def _zoom_in(self) -> None:
        self.scale(self.ZOOM_IN_FACTOR, self.ZOOM_IN_FACTOR)

    def _zoom_out(self) -> None:
        self.scale(self.ZOOM_OUT_FACTOR, self.ZOOM_OUT_FACTOR)

    def _repaint(self) -> None:
        """Make scene repaint for component update"""
        self._app_model.sig_repaint.emit()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """QT event callback function"""
        super().keyPressEvent(event)
        if event.isAutoRepeat():
            return
        if event.key() == Qt.Key.Key_Shift:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            event.accept()
        elif event.key() == Qt.Key.Key_Control:
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self._wheel_zoom_mode = True
            event.accept()

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        """QT event callback function"""
        super().keyReleaseEvent(event)
        if event.isAutoRepeat():
            return
        if event.key() == Qt.Key.Key_Shift:
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            event.accept()
        elif event.key() == Qt.Key.Key_Control:
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self._wheel_zoom_mode = False
            event.accept()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """QT event callback function"""
        event.accept()
        self._show_drag_preview(event.mimeData().text(), event.position().toPoint())

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:
        """QT event callback function"""
        event.accept()
        self._remove_drag_preview()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        """QT event callback function"""
        event.accept()
        if self._drag_preview is not None:
            self._drag_preview.setPos(self.mapToScene(event.position().toPoint()))

    def _show_drag_preview(self, name: str, view_pos: QPoint) -> None:
        """
        Show a see-through preview of the component where it will be dropped. The drag
        image, drawn by the window system, is missing in some Wayland sessions.
        """
        self._remove_drag_preview()
        preview_image = drag_preview(self._app_model, name)
        if preview_image is None:
            # Not a component, for example text dragged from another application
            return
        pixmap, center = preview_image
        # Keep the view still when the preview is added to the scene
        self.grow_scene_rect()
        preview = QGraphicsPixmapItem(pixmap)
        preview.setOffset(-center)
        preview.setOpacity(0.5)
        preview.setZValue(1e9)
        preview.setPos(self.mapToScene(view_pos))
        self._scene.addItem(preview)
        self._drag_preview = preview

    def _remove_drag_preview(self) -> None:
        if self._drag_preview is not None:
            if self._drag_preview.scene() is not None:
                self._scene.removeItem(self._drag_preview)
            self._drag_preview = None

    def dropEvent(self, event: QDropEvent) -> None:
        """QT event callback function"""
        event.setDropAction(Qt.DropAction.IgnoreAction)
        event.accept()
        self.setFocus()
        self._remove_drag_preview()

        scene_pos = self.mapToScene(event.position().toPoint())

        component_name = event.mimeData().text()
        QTimer.singleShot(0, partial(self.add_component, component_name, scene_pos))

    def enterEvent(self, event: QEvent) -> None:
        """QT event callback function"""
        self.setFocus()
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """QT event callback function"""
        super().mouseMoveEvent(event)
        self._mouse_pos = event.position().toPoint()
        # Draw unfinished wire
        if self._app_model.objects.new_wire.ongoing():
            scene_pos = self.mapToScene(self._mouse_pos)
            self._app_model.objects.new_wire.set_end_pos(scene_pos)
            self._repaint()

    def wheelEvent(self, event: QWheelEvent) -> None:
        """QT event callback function"""
        # Zoom on wheel
        if not self._wheel_zoom_mode:
            super().wheelEvent(event)
            return
        wheel_steps = event.angleDelta().y()
        if wheel_steps != 0:
            before = self.mapToScene(self._mouse_pos)
            if wheel_steps > 0:
                self._zoom_in()
            else:
                self._zoom_out()
            # Keep the point under the mouse pointer in place
            translation = self.mapToScene(self._mouse_pos) - before
            self.translate(translation.x(), translation.y())
        event.accept()

    def add_component(self, name: str, position: QPointF | None) -> None:
        """
        Add component to circuit area
        Used by drag'n'drop into Circuit area (centered at 'position')
        or double click in SelectableComponentWidget (position is None)
        """
        centered = position is not None
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
            if component_object is None:
                return
            if centered:
                component_object.move_center_to(position)
            self.grow_scene_rect()
            self._scene.add_scene_component(component_object, True)
            self.grow_scene_rect()

    def grow_scene_rect(self) -> None:
        """
        Grow the scene to include all components and the visible area. Otherwise the
        scene follows the components, and when a component makes it larger the view
        re-centers and everything on screen moves.
        """
        visible = self.mapToScene(self.viewport().rect()).boundingRect()
        self._scene.setSceneRect(
            self._scene.sceneRect().united(self._scene.itemsBoundingRect()).united(visible)
        )
