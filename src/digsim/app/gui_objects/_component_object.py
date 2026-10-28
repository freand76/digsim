# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""A component placed in the GUI"""

from __future__ import annotations

import abc
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QTransform
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsRectItem,
    QGraphicsSceneContextMenuEvent,
    QGraphicsSceneHoverEvent,
    QGraphicsSceneMouseEvent,
    QMenu,
    QStyleOptionGraphicsItem,
    QWidget,
)

from digsim.app._wire_route import default_direction, rotated
from digsim.circuit.components.atoms import Component, Port
from digsim.storage_model import GuiPositionDataClass

from . import _theme as theme
from ._component_context_menu import ComponentContextMenu
from ._component_port_item import PortGraphicsItem


if TYPE_CHECKING:
    from digsim.app.model import AppModel


class ComponentObject(QGraphicsRectItem):
    """A component graphics item, a 'clickable' item with a custom paintEvent"""

    DEFAULT_WIDTH = 40
    DEFAULT_HEIGHT = 40
    RECT_TO_BORDER = 5
    BORDER_TO_PORT = 10
    PORT_SIDE = 8
    DEFAULT_PORT_TO_PORT_DISTANCE = 20
    # Draw the port names next to the ports
    SHOW_PORT_NAMES = True
    # Draw the ports on the border as arrows that show their direction, not as dots
    PORT_ARROWS = False
    # How far outside its rect the component paints, like the glow of a lit LED
    PAINT_MARGIN = 0
    # Can be rotated, a quarter at a time
    ROTATABLE = False

    _COMPONENT_NAME_FONT = theme.font(8, bold=True)
    _PORT_NAME_FONT = theme.font(7)
    _SELECTABLE_COMPONENT_NAME_FONT = theme.font(8)

    def __init__(
        self,
        app_model: AppModel,
        component: Component,
        xpos: float,
        ypos: float,
        port_distance: int = DEFAULT_PORT_TO_PORT_DISTANCE,
    ) -> None:
        super().__init__(QRect(int(xpos), int(ypos), self.DEFAULT_WIDTH, self.DEFAULT_HEIGHT))
        self._app_model = app_model
        self._component = component
        self._port_distance = port_distance

        # Class variables
        # The name shown for each port (with its bit range for a bus), and its graphics item
        self._port_names: dict[Port, str] = {}
        self._port_items: dict[Port, PortGraphicsItem] = {}
        self._parent_widget: QWidget | None = None
        self._mouse_press_pos: QPoint | None = None
        self._moved = False
        self._save_pos: QPointF | QPoint = self.rect().topLeft()
        # Clockwise, around the middle of the rect: 0, 90, 180 or 270 degrees
        self._rotation = 0

        # Create ports
        self.create_ports()

        # Qt Flags
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)

    def control_notify(self) -> None:
        """Called when the simulation is started or stopped"""
        if self._app_model.is_running:
            self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
            self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, False)
        else:
            self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
            self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)

    def disconnect(self) -> None:
        """
        Called before the component object is removed.
        GUI objects don't connect to the model's signals themselves: the signals are
        often queued (sent from the simulation thread), and a queued call to a removed
        object would run on freed memory. The circuit area forwards them instead.
        """

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value: Any) -> Any:
        """QT event callback function"""
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self._moved = True
            # Also when it moves with other selected components (only the one under the
            # mouse gets the release)
            self._save_pos = (self.rect().topLeft() + self.pos()).toPoint()
        elif change == QGraphicsItem.GraphicsItemChange.ItemSelectedChange:
            if self._app_model.is_running:
                value = 0
        elif change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            self.repaint()
        return super().itemChange(change, value)

    def hoverEnterEvent(self, _: QGraphicsSceneHoverEvent) -> None:
        """QT event callback function"""
        if self._app_model.is_running and self.component.has_action:
            self.setCursor(Qt.CursorShape.PointingHandCursor)

    def hoverLeaveEvent(self, _: QGraphicsSceneHoverEvent) -> None:
        """QT event callback function"""
        self.setCursor(Qt.CursorShape.ArrowCursor)

    def hoverMoveEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        """QT event callback function"""
        self.mouse_position(event.scenePos())
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """QT event callback function"""
        super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            if self._app_model.is_running:
                self._app_model.model_add_event(self.component.onpress)
            else:
                self._mouse_press_pos = event.screenPos()
                self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """QT event callback function"""
        super().mouseReleaseEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            if self._app_model.is_running:
                self._app_model.model_add_event(self.component.onrelease)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
                if event.screenPos() != self._mouse_press_pos:
                    # Move completed, set model to changed
                    self._app_model.objects.components.component_moved()
                    position = self.rect().topLeft() + self.pos()
                    self._save_pos = position.toPoint()
                else:
                    if not self._app_model.objects.new_wire.ongoing():
                        self.single_click_action()
        self._mouse_press_pos = None

    def contextMenuEvent(self, event: QGraphicsSceneContextMenuEvent) -> None:
        """QT event callback function"""
        if self._app_model.is_running:
            return
        if self._app_model.objects.new_wire.ongoing():
            self._app_model.objects.new_wire.abort()
        context_menu = ComponentContextMenu(self._parent_widget, self._app_model, self)
        context_menu.open_at(event.screenPos())

    def boundingRect(self) -> QRectF:
        """QT function: the rect and the outline, and what is painted outside the rect"""
        # The outline of a selected component is 4 pixels wide at most
        margin = self.PAINT_MARGIN + 2
        return QRectF(self.rect()).adjusted(-margin, -margin, margin, margin)

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        """QT function"""
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.paint_component(painter)
        if self.SHOW_PORT_NAMES:
            self.paint_portnames(painter)

    @property
    def component(self) -> Component:
        """Get component"""
        return self._component

    def has_moved(self) -> bool:
        """True if the component has moved since last call"""
        moved = self._moved
        self._moved = False
        return moved

    def create_ports(self) -> None:
        """Create ports for component object"""
        for port in self._component.ports:
            if port.width == 1:
                self._port_names[port] = port.name()
            else:
                self._port_names[port] = f"{port.name()}[{port.width - 1}:0]"
            self._port_items[port] = PortGraphicsItem(
                self._app_model, self, port, arrow=self.PORT_ARROWS
            )
        self.update_ports()

    def update_ports(self) -> None:
        """Update port positions for the placed component"""

        # Make sure all ports fit in the height of the component
        max_ports = max(len(self._component.inports()), len(self._component.outports()))
        if max_ports > 1:
            min_height = (max_ports - 1) * self._port_distance + 2 * self.BORDER_TO_PORT
            self.height = max(self.height, min_height)

        # Make sure port names fit in the width of the component
        if self.SHOW_PORT_NAMES:
            self._fit_port_names()

        # Create port rects
        self._set_port_rects(self._component.inports(), -self.RECT_TO_BORDER)
        self._set_port_rects(
            self._component.outports(), self.RECT_TO_BORDER + self.width - self.PORT_SIDE - 1
        )
        self._apply_rotation()

    @property
    def rotation_angle(self) -> int:
        """The rotation clockwise, 0, 90, 180 or 270 degrees"""
        return self._rotation

    @rotation_angle.setter
    def rotation_angle(self, rotation: int) -> None:
        self._rotation = rotation % 360 if self.ROTATABLE else 0
        self._apply_rotation()

    def _apply_rotation(self) -> None:
        """Rotate the component and its ports around the middle of its rect"""
        center = self.rect().center()
        self.setTransform(
            QTransform()
            .translate(center.x(), center.y())
            .rotate(self._rotation)
            .translate(-center.x(), -center.y())
        )

    def port_direction(self, port: Port) -> str:
        """The direction a wire leaves a port in, see digsim.app._wire_route"""
        return rotated(default_direction(port.is_output()), self._rotation)

    def _fit_port_names(self) -> None:
        """Make the component wide enough for the names of its ports"""
        max_inport_name = ""
        max_outport_name = ""
        for port in self.component.ports:
            port_name = self._port_names[port]
            # An inout port is on the right side, with the outputs
            if not port.is_output() and len(port_name) > len(max_inport_name):
                max_inport_name = port_name
            elif port.is_output() and len(port_name) > len(max_outport_name):
                max_outport_name = port_name
        max_port_names = f"{max_inport_name} {max_outport_name}"
        max_port_names_w, _ = self.get_string_metrics(max_port_names)
        self.width = max(2 * self.inport_x_pos() + max_port_names_w, self.width)

    def get_port_item(self, port: Port) -> PortGraphicsItem:
        """Get port item"""
        return self._port_items[port]

    def set_port_rect(self, port: Port, rect: QRect | QRectF) -> None:
        """Set port rect"""
        self.get_port_item(port).setRect(rect)

    def _set_port_rects(self, ports: list[Port], xpos: float) -> None:
        """Place the ports at 'xpos', spread evenly around the vertical center"""
        top_to_port = (self.height - self._port_distance * (len(ports) - 1)) / 2
        for idx, port in enumerate(ports):
            rect = QRect(
                int(self.object_pos.x() + xpos),
                int(
                    self.object_pos.y()
                    + top_to_port
                    + idx * self._port_distance
                    - self.PORT_SIDE / 2
                ),
                self.PORT_SIDE,
                self.PORT_SIDE,
            )
            self.get_port_item(port).setRect(rect)

    def set_parent_widget(self, parent: QWidget) -> None:
        """Set the parent"""
        self._parent_widget = parent

    @property
    def selected(self) -> bool:
        """Get the selected variable for the current object"""
        return self.isSelected()

    def repaint(self) -> None:
        """Update GUI for this component object"""
        self._app_model.sig_repaint.emit()

    def get_string_metrics(self, port_str: str, font: QFont | None = None) -> tuple[int, int]:
        """Get the port display name (including bits if available)"""
        if font is None:
            font = self._PORT_NAME_FONT
        fm = QFontMetrics(font)
        str_pixels_w = fm.horizontalAdvance(port_str)
        str_pixels_h = fm.height()
        return str_pixels_w, str_pixels_h

    def paint_component_name(self, painter: QPainter) -> None:
        """Paint the component name"""
        painter.setPen(theme.INK)
        painter.setFont(self._COMPONENT_NAME_FONT)
        fm = QFontMetrics(self._COMPONENT_NAME_FONT)
        display_name_str = self._component.display_name()
        str_pixels_w = fm.horizontalAdvance(display_name_str)
        str_pixels_h = fm.height()
        painter.drawText(
            int(self.rect().x() + self.rect().width() / 2 - str_pixels_w / 2),
            int(self.rect().y() + str_pixels_h + 1),
            display_name_str,
        )

    def paint_component_base(
        self, painter: QPainter, color: QColor | Qt.GlobalColor = theme.BODY
    ) -> None:
        """Paint the body of the component, white unless another color is given"""
        theme.paint_body(painter, self.rect(), self.selected, QColor(color))

    @abc.abstractmethod
    def paint_component(self, painter: QPainter) -> None:
        """Paint component"""

    @classmethod
    @abc.abstractmethod
    def paint_selectable_component(cls, painter: QPainter, size: QSize, name: str) -> None:
        """
        Paint selectable component
        use width x width (square) to paint component image
        """

    @classmethod
    def paint_selectable_component_name(
        cls, painter: QPainter, point: QPoint | QPointF, size: QSize, name: str
    ) -> None:
        """Paint the name for the selectable component"""
        painter.setFont(cls._SELECTABLE_COMPONENT_NAME_FONT)
        fm = QFontMetrics(cls._SELECTABLE_COMPONENT_NAME_FONT)
        str_pixels_w = fm.horizontalAdvance(name)
        str_pixels_h = fm.height()
        painter.setPen(theme.INK)
        painter.drawText(
            int(point.x() + size.width() / 2 - str_pixels_w / 2),
            int(point.y() + size.height() - str_pixels_h),
            name,
        )

    def inport_x_pos(self) -> float:
        """Get the X position left of the input port"""
        return 1.5 * self.PORT_SIDE

    def paint_portnames(
        self, painter: QPainter, color: QColor | Qt.GlobalColor = theme.INK
    ) -> None:
        """Paint component ports"""
        painter.setPen(color)
        painter.setFont(self._PORT_NAME_FONT)
        # Room for the arrows, which are mostly inside the body
        gap = 2 if self.PORT_ARROWS else 0
        for port in self._component.ports:
            rect = self.get_port_item(port).rect()
            port_str = self._port_names[port]
            str_pixels_w, str_pixels_h = self.get_string_metrics(port_str, self._PORT_NAME_FONT)
            text_y = rect.y() + str_pixels_h - self.PORT_SIDE / 2
            if rect.x() < self.object_pos.x():
                text_pos = QPoint(int(rect.x() + self.inport_x_pos() + gap), int(text_y))
            else:
                text_pos = QPoint(
                    int(rect.x() - str_pixels_w - self.PORT_SIDE / 2 - gap), int(text_y)
                )
            painter.drawText(text_pos, port_str)

    def get_port_pos(self, portname: str) -> QPointF:
        """Get component port pos"""
        port = self.component.port(portname)
        return self.get_port_item(port).rect().center()

    def mouse_position(self, pos: QPointF) -> None:
        """Component function: called for mouse position update"""

    def single_click_action(self) -> None:
        """Component function:: called for mouse single click"""

    def add_context_menu_action(self, menu: QMenu, parent: QWidget | None) -> None:
        """Component function:: called when context menu is created"""

    def update_size(self) -> None:
        """Component function: called when the component can update its size"""

    @property
    def size(self) -> QSize:
        """Get size"""
        return QSize(int(self.width), int(self.height))

    @property
    def object_pos(self) -> QPointF:
        """Get position"""
        return self.rect().topLeft()

    @property
    def width(self) -> float:
        """Get width"""
        return self.rect().width()

    @width.setter
    def width(self, width: float) -> None:
        """Set width"""
        self.setRect(self.rect().x(), self.rect().y(), width, self.rect().height())

    @property
    def height(self) -> float:
        """Get height"""
        return self.rect().height()

    @height.setter
    def height(self, height: float) -> None:
        """Set height"""
        self.setRect(self.rect().x(), self.rect().y(), self.rect().width(), height)

    @property
    def zlevel(self) -> float:
        """Get zlevel"""
        return self.zValue()

    @zlevel.setter
    def zlevel(self, level: float) -> None:
        """Set zlevel"""
        self.setZValue(level)

    def move_center_to(self, scene_pos: QPointF) -> None:
        """Move the component so that its center is at 'scene_pos'"""
        center = self.mapRectToScene(self.rect()).center()
        self.moveBy(scene_pos.x() - center.x(), scene_pos.y() - center.y())
        self._save_pos = (self.rect().topLeft() + self.pos()).toPoint()

    def to_gui_dataclass(self) -> GuiPositionDataClass:
        return GuiPositionDataClass(
            x=int(self._save_pos.x()),
            y=int(self._save_pos.y()),
            z=int(self.zlevel),
            rotation=self._rotation,
        )
