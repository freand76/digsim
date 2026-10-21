# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""The circuit area and component widget"""

from __future__ import annotations

from collections.abc import Callable
from functools import partial
from itertools import pairwise
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
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsPathItem,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSceneContextMenuEvent,
    QGraphicsSceneHoverEvent,
    QGraphicsSceneMouseEvent,
    QGraphicsView,
    QMenu,
    QStyleOptionGraphicsItem,
    QWidget,
)

from digsim.app._line_graph import junctions, on_segment
from digsim.app._wire_key import Wire
from digsim.app._wire_lines import At, GraphSegment, Node, PointMove
from digsim.app._wire_path import (
    Point,
    Rect,
    can_merge_segments,
    corner_at,
    corner_points,
    drawing_points,
    exits_vertically,
    follow_joint,
    handle_at,
    is_movable,
    is_vertical,
    merge_corner,
    merge_segments,
    move_segment,
    nearest_segment,
    split_at_port,
    split_corner,
    split_segment,
)
from digsim.app.gui_objects import ComponentObject
from digsim.app.gui_objects._buzzer_object import BuzzerObject
from digsim.app.gui_objects._component_port_item import PortGraphicsItem
from digsim.app.settings import ComponentSettingsDialog
from digsim.circuit.components.atoms import VALUE_TYPE, Component, Port, PortConnectionError

from ._drag_preview import drag_preview


if TYPE_CHECKING:
    from digsim.app.model import AppModel


def _point(pos: QPointF) -> Point:
    return pos.x(), pos.y()


def _rect(rect: QRectF) -> Rect:
    return rect.x(), rect.y(), rect.width(), rect.height()


class WirePartGraphicsItem(QGraphicsRectItem):
    """
    A segment of a wire graphics item. When the wire is selected, the segments that are not
    attached to a port have a dot in the middle, and can be dragged by it. Close to a
    corner, the segments' areas overlap, so the mouse works on the dot or segment under it,
    which may belong to another part.
    """

    CLOSE_TO_WIRE_MARGIN = 10
    # The radius of the dot that shows that a segment of a selected wire can be dragged
    HANDLE_RADIUS = 4
    # How close to the middle of the dot the mouse must be to drag the segment
    HANDLE_GRAB_RADIUS = 8

    # The radius of the dot where a branch starts on another wire
    JUNCTION_RADIUS = 5
    # How close to a corner the mouse must be to start a new wire there
    CORNER_RADIUS = 5
    # The radius of the ring that shows a joint of a selected wire
    JOINT_RADIUS = 4

    def __init__(
        self,
        app_model: AppModel,
        src_port: Port,
        parent: WireGraphicsItem,
        segment: int,
        point_pair: tuple[Point, Point],
    ) -> None:
        self._app_model = app_model
        self._src_port = src_port
        self._parent = parent
        self._segment = segment
        self._start = QPointF()
        self._end = QPointF()
        # The dots that this segment draws, where its line goes three or more ways, and
        # the segments there (the dot is black when one of them is selected)
        self._dots: list[tuple[Point, list[WirePartGraphicsItem]]] = []
        self._selected = False
        # The segment being dragged
        self._drag_segment: int | None = None
        # A press that started a new wire or selected the tree, the release must not
        # change the selection
        self._handled_press = False
        super().__init__(QRectF(), parent)
        self.set_points(point_pair)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setAcceptHoverEvents(True)

    def set_points(self, point_pair: tuple[Point, Point]) -> None:
        """Set the start and end of the segment"""
        (src_x, src_y), (dst_x, dst_y) = point_pair
        x_low, x_high = min(src_x, dst_x), max(src_x, dst_x)
        y_low, y_high = min(src_y, dst_y), max(src_y, dst_y)
        self._start = QPointF(x_low, y_low)
        self._end = QPointF(x_high, y_high)
        self.setRect(
            QRectF(
                x_low - self.CLOSE_TO_WIRE_MARGIN,
                y_low - self.CLOSE_TO_WIRE_MARGIN,
                x_high - x_low + 2 * self.CLOSE_TO_WIRE_MARGIN,
                y_high - y_low + 2 * self.CLOSE_TO_WIRE_MARGIN,
            )
        )

    def is_wire_selected(self) -> bool:
        """Is the segment shown as selected"""
        return self._selected

    def wire_selected(self, selected: bool) -> None:
        """Set Wire Selected"""
        self._selected = selected
        if not selected:
            self.unsetCursor()
        # The color and the dots change
        self.update()

    def hoverMoveEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        """QT event callback function"""
        # Over a dot or a joint, the cursor shows that it can be dragged, and how. While a
        # wire is drawn, that it can end here.
        segment = self._handle_at(event.scenePos())
        if segment is None:
            # A point where wires meet, or a joint, moves along the straight line through
            # it, across the segment that moves
            scene = self.scene()
            move = (
                scene.point_move_at(event.scenePos())
                if isinstance(scene, _CircuitAreaScene)
                else None
            )
            segment = None if move is None else move.segment
        if segment is not None:
            if is_vertical(segment):
                self.setCursor(Qt.CursorShape.SizeHorCursor)
            else:
                self.setCursor(Qt.CursorShape.SizeVerCursor)
        elif self._corner_at(event.scenePos()) is not None or self._can_end_at(event.scenePos()):
            self.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.unsetCursor()
        super().hoverMoveEvent(event)

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value: Any) -> Any:
        """QT event callback function"""
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedChange:
            # Like components, wires can't be selected while the simulation runs
            if self._app_model.is_running:
                value = False
        elif change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            scene = self.scene()
            if isinstance(scene, _CircuitAreaScene):
                scene.wire_selection_changed()
        return super().itemChange(change, value)

    @property
    def segment(self) -> int:
        """The number of the segment in its wire"""
        return self._segment

    def touches(self, point: Point) -> bool:
        """Does the segment have a length, and end at or run through a point"""
        start, end = _point(self._start), _point(self._end)
        return start != end and on_segment(start, end, point)

    @property
    def dots(self) -> list[Point]:
        """The dots that this segment draws"""
        return [point for point, _ in self._dots]

    def ring(self) -> Point | None:
        """Where the segment shows a joint (a ring), on a selected wire"""
        if self._is_joint() and self._selected and not self._app_model.is_running:
            return _point(self._start)
        return None

    def set_dots(self, dots: list[tuple[Point, list[WirePartGraphicsItem]]]) -> None:
        """The dots that this segment draws, and the segments at each"""
        if dots != self._dots:
            self._dots = dots
            self.update()

    def distance(self, scene_pos: QPointF) -> float:
        """The distance from a position to the segment"""
        dist_x = max(self._start.x() - scene_pos.x(), 0, scene_pos.x() - self._end.x())
        dist_y = max(self._start.y() - scene_pos.y(), 0, scene_pos.y() - self._end.y())
        return max(dist_x, dist_y)

    @property
    def wire_item(self) -> WireGraphicsItem:
        """The wire that the segment belongs to"""
        return self._parent

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """QT event callback function"""
        if event.button() == Qt.MouseButton.RightButton and not self._app_model.is_running:
            # The wire is selected while its context menu is open, like after a left click
            # (otherwise the scene would take the press as a click beside it)
            if not self._selected:
                self.scene().clearSelection()
                self.setSelected(True)
            event.accept()
            return
        # A segment of a selected wire is dragged by its dot, and a joint along the wire
        # (a new wire starts on a wire from the context menu). A click selects the wires
        # through the segment, from the output port to their input ports, and a click on
        # a selected wire selects its whole tree.
        self._drag_segment = None
        self._handled_press = False
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_segment = self._handle_at(event.scenePos())
            if self._drag_segment is not None and self._parent.is_port_segment(self._drag_segment):
                # Split when it is dragged, see the scene
                self._drag_segment = None
            plain_click = event.modifiers() == Qt.KeyboardModifier.NoModifier
            if self._drag_segment is None and self._selected and plain_click:
                self._parent.select_tree()
                self._handled_press = True
                event.accept()
                return
        super().mousePressEvent(event)

    def handle_at(self, scene_pos: QPointF) -> int | None:
        """The segment with its dot at a position, see _handle_at()"""
        return self._handle_at(scene_pos)

    def _handle_at(self, scene_pos: QPointF) -> int | None:
        """The segment with its dot at a position, if the wire's segments can be dragged"""
        if not self._selected or self._app_model.is_running:
            return None
        return self._parent.handle_at(scene_pos, self.HANDLE_GRAB_RADIUS)

    def _corner_at(self, scene_pos: QPointF) -> int | None:
        """The corner at a position, if the wire being drawn can end there"""
        new_wire = self._app_model.objects.new_wire
        if not new_wire.ongoing() or not new_wire.can_end_on_wire(self._parent.wire):
            return None
        return self._parent.corner_at(scene_pos, self.CORNER_RADIUS)

    def _can_end_at(self, scene_pos: QPointF) -> bool:
        """
        Can the wire being drawn end on the segment here: if it connects another line to
        the line of this wire
        """
        return (
            self._app_model.objects.new_wire.can_end_on_wire(self._parent.wire)
            and self.distance(scene_pos) <= self.CORNER_RADIUS
        )

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """QT event callback function"""
        if self._drag_segment is not None:
            self._parent.drag_segment(self._drag_segment, event.scenePos())
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """QT event callback function"""
        if self._drag_segment is not None:
            self._drag_segment = None
            self._parent.drag_finished()
        if self._handled_press:
            self._handled_press = False
            return
        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event: QGraphicsSceneContextMenuEvent) -> None:
        """QT event callback function"""
        if self._app_model.is_running:
            return
        if self._app_model.objects.new_wire.ongoing():
            self._app_model.objects.new_wire.abort()
        event.accept()
        segment = self._parent.nearest_segment(event.scenePos())
        self._parent.context_menu(segment, event.scenePos(), event.screenPos())

    def _get_wire_color(self, port_value: VALUE_TYPE, bus_width: int) -> QColor | Qt.GlobalColor:
        if port_value == "X":
            return Qt.GlobalColor.red
        if port_value == "Z":
            # Not driven, high impedance
            return QColor(64, 112, 255)
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
            # All wires of a line have its value, "X" when its outputs drive different values
            pen.setColor(self._get_wire_color(self._parent.line_value(), bus_width))

        painter.setPen(pen)
        painter.drawLine(self._start, self._end)

        extra_radius = 1 if bus_width > 1 else 0
        for point, parts in self._dots:
            # Where the line goes three or more ways, in its color, or black when a wire
            # there is selected
            painter.setPen(Qt.PenStyle.NoPen)
            if not self._app_model.is_running and any(p.is_wire_selected() for p in parts):
                painter.setBrush(Qt.GlobalColor.black)
            else:
                painter.setBrush(pen.color())
            radius = self.JUNCTION_RADIUS + extra_radius
            painter.drawEllipse(QPointF(*point), radius, radius)
        if self._is_joint() and self._selected and not self._app_model.is_running:
            # A corner of a straight part of the wire, where a new wire can start
            painter.setPen(QPen(Qt.GlobalColor.black, 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            radius = self.JOINT_RADIUS + extra_radius
            painter.drawEllipse(self._start, radius, radius)
        if self._show_handle():
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(Qt.GlobalColor.black)
            radius = self.HANDLE_RADIUS + extra_radius
            painter.drawEllipse((self._start + self._end) / 2, radius, radius)

    def _is_joint(self) -> bool:
        """
        A segment without length between two others in a straight line, that have a
        length: a joint, where the wire doesn't end
        """
        parts = self._parent.part_items
        if self._start != self._end or not 0 < self._segment < len(parts) - 1:
            return False
        before, after = parts[self._segment - 1], parts[self._segment + 1]
        return before._start != before._end and after._start != after._end

    def _show_handle(self) -> bool:
        """A dot in the middle of the segments that can be dragged"""
        return (
            self._selected
            and not self._app_model.is_running
            and (
                self._parent.is_movable(self._segment)
                or self._parent.is_port_segment(self._segment)
            )
            and self._start != self._end
        )


class WireGraphicsItem(QGraphicsPathItem):
    """
    A wire graphics item, drawn from the wire's path in the model. A branch of a wire tree
    starts at a corner of another wire item, its parent. A joined wire ends at a corner of
    the wire item of the line it joins.
    """

    def __init__(
        self,
        app_model: AppModel,
        connection: tuple[Port, Port],
        src_port_item: PortGraphicsItem,
        dst_port_item: PortGraphicsItem,
        branch: tuple[WireGraphicsItem, int] | None = None,
        join: tuple[WireGraphicsItem, int] | None = None,
        line_outputs: list[Port] | None = None,
    ) -> None:
        super().__init__()
        self._app_model = app_model
        self._src_port, self._dst_port = connection
        # The output ports of the wire's line, that give it its value
        self._line_outputs = line_outputs or []
        self._src_port_item = src_port_item
        self._dst_port_item = dst_port_item
        self._branch = branch
        self._join = join
        # The branches that start on this wire, and the joined wires that end on it, they
        # follow it while it is dragged
        self._child_items: list[WireGraphicsItem] = []
        if branch is not None:
            branch[0].add_child_item(self)
        if join is not None:
            join[0].add_child_item(self)
        # A copy, changed while a segment is dragged and stored in the model afterwards
        self._path = list(app_model.objects.wires.path(connection))
        self._part_items: list[WirePartGraphicsItem] = []
        self.setZValue(-1)
        self._selected = False
        self.update_wire()

    @property
    def dst_port(self) -> Port:
        """The input port that the wire drives"""
        return self._dst_port

    def line_value(self) -> VALUE_TYPE:
        """The value of the wire's line: what its output ports drive together"""
        return self._app_model.objects.wires.value(self._line_outputs)

    @property
    def wire(self) -> Wire:
        """The wire, by its two ports (see Wire), as the model knows it"""
        return self._src_port, self._dst_port

    def highlight(self, first: int | None) -> None:
        """Show the wire as selected from a segment to its input port, or not (None)"""
        self.highlight_segments(
            set() if first is None else {item.segment for item in self._part_items[first:]}
        )

    def highlight_segments(self, segments: set[int]) -> None:
        """Show some segments of the wire as selected"""
        for item in self._part_items:
            item.wire_selected(item.segment in segments)
        self._selected = bool(segments)
        if self._selected:
            self.setZValue(self._app_model.objects.components.get_top_zlevel() + 1)
        else:
            self.setZValue(-1)

    def select_segment(self, segment: int) -> None:
        """Select the wires through a segment, like a click on it"""
        self._part_items[min(segment, len(self._part_items) - 1)].setSelected(True)

    def select_tree(self) -> None:
        """Select all wires of the line"""
        scene = self.scene()
        if isinstance(scene, _CircuitAreaScene):
            scene.select_wire_tree(self.wire)

    def is_selected(self) -> bool:
        """Is a part of the wire selected"""
        return self._selected

    def selected_segments(self) -> list[int]:
        """The segments that are selected themselves (clicked), not just highlighted"""
        return [item.segment for item in self._part_items if item.isSelected()]

    def is_movable(self, segment: int) -> bool:
        """True if the segment can be moved (it is not attached to a port)"""
        return is_movable(self._path, segment)

    def is_segment_selected(self, segment: int) -> bool:
        """Is a segment shown as selected"""
        return self._part_items[segment].is_wire_selected()

    @property
    def part_items(self) -> list[WirePartGraphicsItem]:
        """The segments of the wire"""
        return self._part_items

    def segment_count(self) -> int:
        """The number of segments of the wire"""
        return len(self._part_items)

    def is_branch(self) -> bool:
        """True if the wire starts on another wire, not at the output port"""
        return self._branch is not None

    def is_joined(self) -> bool:
        """True if the wire ends on another wire (it joins its line), not at its port"""
        return self._join is not None

    def add_child_item(self, item: WireGraphicsItem) -> None:
        """A branch that starts on this wire, or a joined wire that ends on it"""
        self._child_items.append(item)

    def start_point(self) -> Point:
        """Where the wire starts: at the output port, or at a corner of its parent"""
        if self._branch is not None:
            parent, corner = self._branch
            return parent.corner_points()[corner]
        return _point(self._src_port_item.portPos())

    def end_point(self) -> Point:
        """Where the wire ends: at the input port, or at a corner of the line it joins"""
        if self._join is not None:
            line, corner = self._join
            return line.corner_points()[corner]
        return _point(self._dst_port_item.portPos())

    def _port_points(self) -> tuple[Point, Point]:
        return self.start_point(), self.end_point()

    def corner_points(self) -> list[Point]:
        """The points of the wire, from where it starts to the input port"""
        return corner_points(*self._port_points(), self._path)

    def handle_at(self, scene_pos: QPointF, radius: float) -> int | None:
        """
        The segment with its handle (the dot) within 'radius' of a position: a movable
        segment, or a segment at a port (see split_for_drag())
        """
        at_ports = (self._branch is None, self._join is None)
        return handle_at(*self._port_points(), self._path, _point(scene_pos), radius, at_ports)

    def is_port_segment(self, segment: int) -> bool:
        """Is a segment attached to a port: the first or the last, at the port"""
        return (segment == 0 and self._branch is None) or (
            segment == len(self._path) + 1 and self._join is None
        )

    def split_for_drag(self, segment: int) -> int:
        """
        A segment at a port is dragged: it is split next to the port (see
        split_at_port()), the wires that start or end on this wire keep their corner.
        Returns the segment that moves. The new path is stored when the drag is finished.
        """
        path, moving = split_at_port(*self._port_points(), self._path, segment)
        for child in self._child_items:
            if child._branch is not None and child._branch[0] is self:
                child._branch = (self, split_corner(segment, child._branch[1]))
            if child._join is not None and child._join[0] is self:
                child._join = (self, split_corner(segment, child._join[1]))
        self._path = path

        def new_segments(old: int) -> list[int]:
            # The split segment is three now: the step next to the port, and the rest
            if old < segment:
                return [old]
            return [segment, segment + 1, segment + 2] if old == segment else [old + 2]

        clicked = [
            new
            for part in self._part_items
            if part.isSelected()
            for new in new_segments(part.segment)
        ]
        shown = {
            new
            for part in self._part_items
            if part.is_wire_selected()
            for new in new_segments(part.segment)
        }
        scene = self.scene()
        for part in self._part_items:
            if scene is not None:
                scene.removeItem(part)
        self.update_wire()
        # Selected as before
        if isinstance(scene, _CircuitAreaScene):
            scene.select_parts([self._part_items[new] for new in clicked])
        self.highlight_segments(shown)
        return moving

    def corner_at(self, scene_pos: QPointF, radius: float) -> int | None:
        """The inner corner within 'radius' of a position"""
        return corner_at(*self._port_points(), self._path, _point(scene_pos), radius)

    def nearest_segment(self, scene_pos: QPointF) -> int:
        """The segment closest to a position"""
        return nearest_segment(*self._port_points(), self._path, (scene_pos.x(), scene_pos.y()))

    def update_wire(self) -> None:
        """Create the segments of the wire"""
        self._part_items = [
            WirePartGraphicsItem(self._app_model, self._src_port, self, segment, point_pair)
            for segment, point_pair in enumerate(pairwise(self.corner_points()))
        ]

    def _move_parts(self) -> None:
        """Move the segments to the current path, and the branches with them"""
        for item, point_pair in zip(self._part_items, pairwise(self.corner_points()), strict=True):
            item.set_points(point_pair)
            # The junction dot moves too
            item.update()
        for child in self._child_items:
            child._move_parts()

    def drag_segment(self, segment: int, scene_pos: QPointF) -> None:
        """Move a segment to the mouse position, sideways or up and down"""
        position = scene_pos.x() if is_vertical(segment) else scene_pos.y()
        self._path = move_segment(self._path, segment, round(position))
        self._move_parts()
        scene = self.scene()
        if isinstance(scene, _CircuitAreaScene):
            # The dots of the line move with the wires
            scene.update_dots(self)

    def drag_finished(self, corner_map: Callable[[int], int] | None = None) -> None:
        """
        Store the new path in the model (an undo step), 'corner_map' gives the new corner
        of the old ones, if the drag added corners
        """
        self._app_model.objects.wires.set_path(self.wire, self._path, corner_map)
        # The pieces of the line can be others now (a segment got a length, or lost it).
        # Not now: the wire items are replaced, and this one is handling an event.
        QTimer.singleShot(0, self._app_model.sig_update_wires.emit)

    def drag_point(self, move: PointMove, scene_pos: QPointF) -> float:
        """
        Move a point where wires meet, or a joint, to the mouse (see
        ModelWires.point_move()): the segment of this wire across it moves. Returns where.
        """
        segment = move.segment
        position = scene_pos.x() if is_vertical(segment) else scene_pos.y()
        position = min(max(round(position), move.bounds[0]), move.bounds[1])
        old = self._path[segment - 1]
        self._path = move_segment(self._path, segment, position)
        # The wires that start or end at the point follow it, like
        # ModelWires.joint_followers() (with the path shown, maybe split)
        for child in self._child_items:
            branch, join = child._branch, child._join
            path = follow_joint(
                segment,
                old,
                position,
                child._path,
                branch[1] if branch is not None and branch[0] is self else None,
                join[1] if join is not None and join[0] is self else None,
            )
            if path is not None:
                child._path = path
        self._move_parts()
        scene = self.scene()
        if isinstance(scene, _CircuitAreaScene):
            scene.update_dots(self)
        return position

    def drag_point_finished(self, move: PointMove, position: float) -> None:
        """Store where the point was moved to in the model (an undo step)"""
        self._app_model.objects.wires.move_point(move, position)
        # Not now: the wire items are replaced, and this one is handling an event
        QTimer.singleShot(0, self._app_model.sig_update_wires.emit)

    def context_menu(self, segment: int, scene_pos: QPointF, screen_pos: QPoint) -> None:
        """The context menu of a segment, to split it or merge it with its neighbors"""
        menu = QMenu()
        split_action = menu.addAction("Split segment")
        split_action.triggered.connect(partial(self._split_segment, segment, scene_pos))
        start_action = menu.addAction("Start wire here")
        start_action.triggered.connect(partial(self._start_wire, segment, scene_pos))
        merge_action = menu.addAction("Merge segments")
        joint = self._app_model.objects.wires.unused_joint(self.wire, segment)
        merge_action.setEnabled(joint is not None or can_merge_segments(self._path, segment))
        if joint is not None:
            # Segments in a straight line: without the joint between them
            merge_action.triggered.connect(partial(self._remove_joint, segment))
        else:
            merge_action.triggered.connect(partial(self._merge_segments, segment))
        menu.addSeparator()
        tree_action = menu.addAction("Select wire tree")
        tree_action.triggered.connect(self.select_tree)
        menu.addSeparator()
        automatic = self._app_model.objects.wires.automatic_path(self.wire)
        automatic_action = menu.addAction("Automatic route")
        automatic_action.setEnabled(automatic != self._path)
        automatic_action.triggered.connect(partial(self._change_path, automatic))
        menu.exec(screen_pos)

    def _split_segment(self, segment: int, scene_pos: QPointF) -> None:
        at = (round(scene_pos.x()), round(scene_pos.y()))
        path = split_segment(*self._port_points(), self._path, segment, at)
        self._change_path(path, partial(split_corner, segment))

    def _remove_joint(self, segment: int) -> None:
        self._app_model.objects.wires.remove_joint(self.wire, segment)
        # Not now: the wire items are replaced, and this one is handling an event
        QTimer.singleShot(0, self._app_model.sig_update_wires.emit)

    def _start_wire(self, segment: int, scene_pos: QPointF) -> None:
        """
        A new wire from a corner (or a joint) close to a position, or from the point on
        the segment, where a joint is added when the wire is finished
        """
        corner = self.corner_at(scene_pos, WirePartGraphicsItem.CORNER_RADIUS)
        # On whole pixels, as the circuit file stores them
        at: At = (
            corner
            if corner is not None
            else (segment, (round(scene_pos.x()), round(scene_pos.y())))
        )
        new_wire = self._app_model.objects.new_wire
        new_wire.start_at_corner(self.wire, at)
        new_wire.set_end_pos(scene_pos)
        scene = self.scene()
        if scene is not None:
            # Not selected while the new wire is drawn: a selected wire is on top, and
            # would cover the ports where the new wire can end
            scene.clearSelection()
        self._app_model.sig_repaint.emit()

    def _merge_segments(self, segment: int) -> None:
        corner_map = partial(merge_corner, self._path, segment)
        self._change_path(merge_segments(self._path, segment), corner_map)

    def _change_path(
        self, path: list[float], corner_map: Callable[[int], int] | None = None
    ) -> None:
        self._app_model.objects.wires.set_path(self.wire, path, corner_map)
        # Not now: the wire items are replaced, and this one is handling an event
        QTimer.singleShot(0, self._app_model.sig_update_wires.emit)


class NewWireGraphicsItem(QGraphicsPathItem):
    """
    The wire being drawn, through the clicked corners and with the corner that a click at
    the mouse position makes
    """

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
        new_wire = self._app_model.objects.new_wire
        start_port = new_wire.start_port()
        end_pos = new_wire.end_pos()
        pen = QPen(Qt.GlobalColor.darkGray)
        if start_port is None or end_pos is None:
            return
        if start_port.width > 1:
            pen.setWidth(4)
        else:
            pen.setWidth(2)
        start_branch = new_wire.start_branch()
        clicks = [*new_wire.clicks(), _point(end_pos)]
        vertical_first = False
        if start_branch is None:
            component_object = self._app_model.objects.components.get_object(start_port.parent())
            start = _point(component_object.get_port_item(start_port).portPos())
        else:
            # Like the model makes it, not along the wire it starts on
            wires = self._app_model.objects.wires
            start = wires.anchor_point(*start_branch)
            taken = wires.anchor_directions(*start_branch)
            vertical_first = exits_vertically(taken, start, clicks[0])
        points = drawing_points(start, clicks, vertical_first)
        painter_path = QPainterPath()
        painter_path.moveTo(QPointF(*points[0]))
        for point in points[1:]:
            painter_path.lineTo(QPointF(*point))
        self.setPath(painter_path)
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
        # The wire items of each line
        self._line_items: dict[Node, list[WireGraphicsItem]] = {}
        # The pieces of lines that are selected (see ModelWires.runs()), the piece of each
        # segment of a wire, and the wires with a selected segment
        self._selected_runs: set[GraphSegment] = set()
        self._runs: dict[tuple[Wire, int], GraphSegment] = {}
        self._selected_wires: set[Wire] = set()
        # Many segments are selected at once, the selection is shown after them
        self._selecting = False
        self._updating_wires = False
        self._select_start_pos: QPointF | None = None
        # The component being dragged, where it was, and the paths of the wires that move
        # with it (between components that move together)
        self._group_move: tuple[ComponentObject, QPointF, dict[Wire, list[float]]] | None = None
        # A selected point where wires meet, or a joint, and what clicks on it selected:
        # 1 the point, 2 the wires there, 3 the whole line
        self._point: Point | None = None
        self._point_stage = 0
        # A pressed point: the point, where the mouse was pressed, if the point was
        # selected then, and when it is dragged, how it moves, its wire and where to
        self._pressed_point: tuple[Point, QPointF, bool] | None = None
        # (how it moves, how it moves in the GUI after a split at a port, its wire, where)
        self._point_drag: tuple[PointMove, PointMove, WireGraphicsItem, float] | None = None
        # A segment at a port that is pressed: its wire, the segment, where the mouse was
        # pressed, and when it is dragged the segment that moves (see split_for_drag())
        self._port_drag: tuple[WireGraphicsItem, int, QPointF, int | None] | None = None
        self._point_marker: QGraphicsEllipseItem
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

    POINT_RADIUS = 8
    # How far the mouse moves on a point before the point is dragged
    POINT_DRAG_DISTANCE = 3

    def point_at(self, pos: QPointF) -> Point | None:
        """
        The point where wires meet (a dot), or the joint of a selected wire (a ring),
        closest to a position, within POINT_RADIUS. Not while a wire is drawn.
        """
        if self._app_model.is_running or self._app_model.objects.new_wire.ongoing():
            return None
        x, y = _point(pos)
        best: tuple[float, Point] | None = None
        for item in self._wire_items:
            for part in item.part_items:
                ring = part.ring()
                for point in [*part.dots, *([ring] if ring is not None else [])]:
                    distance = max(abs(point[0] - x), abs(point[1] - y))
                    if distance <= self.POINT_RADIUS and (best is None or distance < best[0]):
                        best = (distance, point)
        return None if best is None else best[1]

    def _top_wire_part(self, pos: QPointF) -> WirePartGraphicsItem | None:
        """The segment of a wire on top at a position, None if something else is on top"""
        # Not the ring of a point, the wire being drawn or the selection rectangle
        helpers = (self._point_marker, self._selection_rect_item)
        top = next(
            (
                item
                for item in self.items(pos)
                if item not in helpers and not isinstance(item, NewWireGraphicsItem)
            ),
            None,
        )
        return top if isinstance(top, WirePartGraphicsItem) else None

    def _wire_point_at(self, pos: QPointF) -> Point | None:
        """
        The point at a position (see point_at()) if a wire is on top there: not on a port
        or a component, or closer to the dot of a segment that can be dragged
        """
        point = self.point_at(pos)
        if point is None:
            return None
        top = self._top_wire_part(pos)
        if top is None:
            return None
        segment = top.handle_at(pos)
        if segment is not None:
            points = top.wire_item.corner_points()
            (x1, y1), (x2, y2) = points[segment], points[segment + 1]
            x, y = _point(pos)
            to_handle = max(abs((x1 + x2) / 2 - x), abs((y1 + y2) / 2 - y))
            if to_handle <= max(abs(point[0] - x), abs(point[1] - y)):
                return None
        return point

    def point_move_at(self, pos: QPointF) -> PointMove | None:
        """How the point at a position moves, None if there is none or it can't move"""
        point = self._wire_point_at(pos)
        return None if point is None else self._app_model.objects.wires.point_move(point)

    def _select_point(self, point: Point) -> None:
        """Select a point: no wires, the point is shown with a ring around it"""
        self._point, self._point_stage = point, 1
        self.clearSelection()
        self._point_marker.setPos(QPointF(*point))
        self._point_marker.setVisible(True)

    def _clear_point(self) -> None:
        self._point, self._point_stage = None, 0
        self._point_marker.setVisible(False)

    def _drop_drags(self) -> None:
        """
        Forget a drag of a point or a segment at a port, when its wire items are gone (an
        undo while the mouse button is held): its wire can be of the circuit before
        """
        self._pressed_point = None
        self._point_drag = None
        self._port_drag = None

    def selected_point(self) -> Point | None:
        """The point that is selected (not its wires), None if there is none"""
        return self._point if self._point_stage == 1 else None

    def _next_point_selection(self) -> None:
        """A click on the selected point: its wires, then the whole line, then the point"""
        point = self._point
        assert point is not None
        # The wires of the point's line there, not of other lines that cross it
        line = next(
            (
                items
                for items in self._line_items.values()
                if any(
                    point in part.dots or part.ring() == point or part.touches(point)
                    for item in items
                    for part in item.part_items
                )
                and any(point in item.corner_points() for item in items)
            ),
            [],
        )
        parts = [
            part
            for item in line
            for part in item.part_items
            if part.touches(point) or part.ring() == point
        ]
        if self._point_stage == 1 and parts:
            self._point_marker.setVisible(False)
            self.clearSelection()
            for part in parts:
                part.setSelected(True)
            self._point_stage = 2
        elif self._point_stage == 2 and parts:
            parts[0].wire_item.select_tree()
            self._point_stage = 3
        else:
            self._select_point(point)

    def _press_point(self, point: Point, pos: QPointF) -> None:
        self._pressed_point = (point, pos, self._point == point)
        self._point_drag = None
        if self._point != point:
            self._select_point(point)

    def _move_point(self, pos: QPointF) -> None:
        assert self._pressed_point is not None
        point, pressed, _ = self._pressed_point
        if self._point_drag is None:
            moved = pos - pressed
            if max(abs(moved.x()), abs(moved.y())) < self.POINT_DRAG_DISTANCE:
                return
            move = self._app_model.objects.wires.point_move(point)
            item = next((i for i in self._wire_items if move and i.wire == move.wire), None)
            if move is None or item is None:
                return
            self._select_point(point)
            preview = move
            if move.split:
                # A segment at a port: split next to the port now, the model does it again
                preview = move._replace(segment=item.split_for_drag(move.segment), split=False)
            self._point_drag = (move, preview, item, move.bounds[0])
        move, preview, item, _ = self._point_drag
        position = item.drag_point(preview, pos)
        self._point_drag = (move, preview, item, position)
        self._point_marker.setPos(QPointF(*self._moved(point, preview, position)))

    @staticmethod
    def _moved(point: Point, move: PointMove, position: float) -> Point:
        """Where a point is moved to, across the segment that moves"""
        return (position, point[1]) if is_vertical(move.segment) else (point[0], position)

    def _release_point(self) -> None:
        assert self._pressed_point is not None
        point, _, was_selected = self._pressed_point
        self._pressed_point = None
        if self._point_drag is not None:
            move, preview, item, position = self._point_drag
            self._point_drag = None
            self._point = self._moved(point, preview, position)
            item.drag_point_finished(move, position)
        elif was_selected:
            self._next_point_selection()

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """QT event callback function"""
        pos = event.scenePos()
        if event.button() == Qt.MouseButton.LeftButton:
            point = self._wire_point_at(pos)
            if point is not None:
                # A point where wires meet is selected, and dragged if the mouse moves
                self._press_point(point, pos)
                event.accept()
                return
            top = self._top_wire_part(pos)
            segment = None if top is None else top.handle_at(pos)
            if top is not None and segment is not None and top.wire_item.is_port_segment(segment):
                # The dot of a segment at a port: split next to the port when it is dragged
                self._port_drag = (top.wire_item, segment, pos, None)
                event.accept()
                return
        self._clear_point()
        items = self.items(pos)
        new_wire = self._app_model.objects.new_wire
        on_port = any(isinstance(item, PortGraphicsItem) for item in items)
        drawing = new_wire.ongoing() and event.button() == Qt.MouseButton.LeftButton
        if drawing:
            end = self.wire_end_at(pos)
            if end is not None:
                # A wire drawn from an input port ends at a corner of another wire, or
                # anywhere else on it, at a new joint
                wire, number, point = end
                try:
                    if point is None:
                        new_wire.end_at_corner(wire, number)
                    else:
                        new_wire.end_at_joint(wire, number, point)
                except PortConnectionError as exc:
                    new_wire.abort()
                    self._app_model.sig_error.emit(str(exc))
                event.accept()
                self._repaint()
                return
        if drawing and not on_port:
            # A click while drawing a wire, not on the port where it ends: a corner
            new_wire.add_click(pos)
            event.accept()
            self._repaint()
            return
        super().mousePressEvent(event)
        if len(items) == 0:
            self._select_start_pos = pos
        grabber = self.mouseGrabberItem()
        if (
            isinstance(grabber, ComponentObject)
            and event.button() == Qt.MouseButton.LeftButton
            and not self._app_model.is_running
        ):
            self._start_group_move(grabber)
        self._repaint()

    def _start_group_move(self, grabber: ComponentObject) -> None:
        """
        The selected components move together: the wires between them move with them,
        and the move is one undo step, back to the state from before the press
        """
        moving = {
            item.component for item in self.selectedItems() if isinstance(item, ComponentObject)
        }
        moving.add(grabber.component)
        wires = self._app_model.objects.wires
        paths = {wire: list(wires.path(wire)) for wire in wires.moving_wires(moving)}
        self._group_move = (grabber, grabber.pos(), paths)
        self._app_model.objects.components.set_move_undo_state(self._app_model.circuit_to_model())

    def wire_end_at(self, pos: QPointF) -> tuple[Wire, int, Point | None] | None:
        """
        Where the wire being drawn can end on another wire, of another line: the wire on
        top at a position, and its corner close by (wire, corner, None), or the segment
        and the point for a new joint there
        """
        new_wire = self._app_model.objects.new_wire
        if not new_wire.ongoing():
            return None
        items = [item for item in self.items(pos) if not isinstance(item, NewWireGraphicsItem)]
        if items and isinstance(items[0], PortGraphicsItem):
            return None
        for item in items:
            if not isinstance(item, WirePartGraphicsItem):
                continue
            wire = item.wire_item
            if not new_wire.can_end_on_wire(wire.wire):
                continue
            corner = wire.corner_at(pos, WirePartGraphicsItem.CORNER_RADIUS)
            if corner is not None:
                return wire.wire, corner, None
            if item.distance(pos) <= WirePartGraphicsItem.CORNER_RADIUS:
                return wire.wire, item.segment, (round(pos.x()), round(pos.y()))
        return None

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """QT event callback function"""
        if self._pressed_point is not None:
            self._move_point(event.scenePos())
            return
        if self._port_drag is not None:
            item, segment, pressed, moving = self._port_drag
            if moving is None:
                moved = event.scenePos() - pressed
                if max(abs(moved.x()), abs(moved.y())) < self.POINT_DRAG_DISTANCE:
                    return
                moving = item.split_for_drag(segment)
                self._port_drag = (item, segment, pressed, moving)
            item.drag_segment(moving, event.scenePos())
            return
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
            if self._group_move is not None:
                grabber, start, paths = self._group_move
                delta = grabber.pos() - start
                self._app_model.objects.wires.move_paths(paths, round(delta.x()), round(delta.y()))
            self._app_model.sig_update_wires.emit()

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """QT event callback function"""
        if self._pressed_point is not None:
            self._release_point()
            return
        if self._port_drag is not None:
            item, segment, _, moving = self._port_drag
            self._port_drag = None
            if moving is not None:
                item.drag_finished(partial(split_corner, segment))
            return
        super().mouseReleaseEvent(event)
        self._group_move = None
        self._app_model.objects.components.set_move_undo_state(None)
        self._select_start_pos = None
        self._selection_rect_item.setVisible(False)
        # Components may have been moved outside the scene
        self._view.grow_scene_rect()
        self._repaint()

    def _delete_component(self, component_object: ComponentObject) -> None:
        self.removeItem(component_object)
        self._update_wires()

    def _delete_wires(self) -> None:
        """Delete the selected pieces of lines"""
        selected = [
            (item.wire, part.segment)
            for item in self._wire_items
            for part in item.part_items
            if part.is_wire_selected()
        ]
        if selected:
            self._app_model.objects.wires.delete_runs(selected)
            self._update_wires()
            self._app_model.model_changed()

    def wire_selection_changed(self) -> None:
        """
        A segment was selected or deselected: select the pieces of lines that the
        selected segments are on, between ports and points where wires meet, the part
        that Del removes
        """
        if self._updating_wires or self._selecting:
            return
        self._selected_runs = {
            self._runs[(item.wire, segment)]
            for item in self._wire_items
            for segment in item.selected_segments()
            if (item.wire, segment) in self._runs
        }
        self._selected_wires = set()
        for item in self._wire_items:
            shown = set(item.selected_segments()) | {
                part.segment
                for part in item.part_items
                if self._runs.get((item.wire, part.segment)) in self._selected_runs
            }
            item.highlight_segments(shown)
            if shown:
                self._selected_wires.add(item.wire)

    def select_parts(self, parts: list[WirePartGraphicsItem]) -> None:
        """Select segments of wires, without changing what is shown as selected"""
        self._selecting = True
        for part in parts:
            part.setSelected(True)
        self._selecting = False

    def select_wire_tree(self, wire: Wire) -> None:
        """Select all drawn wires of the line of a wire"""
        line = set(self._app_model.objects.wires.line_wires(wire))
        self.clearSelection()
        self._selecting = True
        for item in self._wire_items:
            if item.wire in line:
                for part in item.part_items:
                    part.setSelected(True)
        self._selecting = False
        self.wire_selection_changed()

    def update_dots(self, item: WireGraphicsItem) -> None:
        """Place the dots of the line of a wire again, its wires changed shape"""
        for line_items in self._line_items.values():
            if item in line_items:
                self._update_line_dots(line_items)
                return

    @staticmethod
    def _update_line_dots(line_items: list[WireGraphicsItem]) -> None:
        """
        A dot where the wires of a line go three or more ways, drawn by a segment of the
        line that is there
        """
        parts = [part for item in line_items for part in item.part_items]
        dots: dict[WirePartGraphicsItem, list[tuple[Point, list[WirePartGraphicsItem]]]] = {}
        segments = [pair for item in line_items for pair in pairwise(item.corner_points())]
        for point in junctions(segments):
            touching = [part for part in parts if part.touches(point)]
            if touching:
                dots.setdefault(touching[0], []).append((point, touching))
        for part in parts:
            part.set_dots(dots.get(part, []))

    def _update_wires(self) -> None:
        # The wires are created again, and stay selected (a segment can be gone)
        selected = {
            (item.wire, segment)
            for item in self._wire_items
            for segment in item.selected_segments()
        }
        self._updating_wires = True
        self._drop_drags()
        for item in self._wire_items:
            self.removeItem(item)

        self._wire_items = []
        components = self._app_model.objects.components
        wires = self._app_model.objects.wires
        items: dict[Wire, WireGraphicsItem] = {}
        line_outputs = wires.line_outputs()
        lines = wires.lines()
        self._runs = wires.runs()
        self._line_items = {}
        for src_port, dst_port in wires.drawing_order():
            src_port_item = components.get_object(src_port.parent()).get_port_item(src_port)
            dst_port_item = components.get_object(dst_port.parent()).get_port_item(dst_port)
            branch = wires.branch((src_port, dst_port))
            join = wires.join((src_port, dst_port))
            item = WireGraphicsItem(
                self._app_model,
                (src_port, dst_port),
                src_port_item,
                dst_port_item,
                None if branch is None else (items[branch[0]], branch[1]),
                None if join is None else (items[join[0]], join[1]),
                line_outputs[(src_port, dst_port)],
            )
            items[(src_port, dst_port)] = item
            self.addItem(item)
            self._wire_items.append(item)
            line = lines.find(("wire", (src_port, dst_port)))
            self._line_items.setdefault(line, []).append(item)
        for line_items in self._line_items.values():
            self._update_line_dots(line_items)
        if self._point is not None and not any(
            self._point in item.corner_points() for item in self._wire_items
        ):
            # The point is gone, like after an undo
            self._clear_point()
        self._updating_wires = False
        self._selected_wires = set()
        for item in self._wire_items:
            for wire, segment in selected:
                if item.wire == wire:
                    item.select_segment(segment)
        self.wire_selection_changed()

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
        # A new circuit, nothing is selected
        self._updating_wires = True
        self._drop_drags()
        self.clear()
        # Let the scene size follow the new circuit
        self.setSceneRect(QRectF())
        self._wire_items = []
        self._selected_wires = set()
        # Add new wire item
        self.addItem(NewWireGraphicsItem(self._app_model))
        # Add selection rect
        self._selection_rect_item = QGraphicsRectItem()
        self._selection_rect_item.setPen(Qt.PenStyle.DashLine)
        self._selection_rect_item.setBrush(Qt.BrushStyle.Dense7Pattern)
        self.addItem(self._selection_rect_item)
        # A ring around the selected point, on top of everything
        radius = WirePartGraphicsItem.JUNCTION_RADIUS + 4
        self._point_marker = QGraphicsEllipseItem(-radius, -radius, 2 * radius, 2 * radius)
        self._point_marker.setPen(QPen(Qt.GlobalColor.black, 2))
        self._point_marker.setZValue(1_000_000)
        self._point_marker.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self._point_marker.setVisible(False)
        self.addItem(self._point_marker)
        self._point, self._point_stage = None, 0
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
