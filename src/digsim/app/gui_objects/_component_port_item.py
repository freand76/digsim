# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""A component port graphics item"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QPointF, QRect, QRectF, Qt
from PySide6.QtGui import QPainter, QPolygonF
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsRectItem,
    QGraphicsSceneHoverEvent,
    QGraphicsSceneMouseEvent,
    QStyleOptionGraphicsItem,
    QWidget,
)

from digsim.circuit.components.atoms import Port, PortConnectionError

from . import _theme as theme


if TYPE_CHECKING:
    from digsim.app.model import AppModel


class PortGraphicsItem(QGraphicsRectItem):
    """
    A port graphics item, drawn in its rect (the rect is where it is clicked), as a dot or
    as an arrow (the ports of an IC or a Verilog component): an input points into the
    body, mostly inside it, and an output points out of it, as far out as an inout port.
    An inout port, which both drives its wire and reads it, is a diamond.
    """

    DOT_RADIUS = 2.5
    HOVER_RADIUS = 4.0
    # Half the size of an arrow or a diamond, compared to the radius of a dot
    SHAPE_SCALE = 1.6
    # How much of the length of an input arrow is inside the body
    INPUT_INSIDE = 0.8

    def __init__(
        self, app_model: AppModel, parent: QGraphicsItem, port: Port, arrow: bool = False
    ) -> None:
        super().__init__(QRect(0, 0, 0, 0), parent)
        self._app_model = app_model
        self._port = port
        self._arrow = arrow
        self._hover = False
        self.setAcceptHoverEvents(True)

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        """QT function"""
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(theme.ACCENT if self._hover else theme.INK)
        radius = self.HOVER_RADIUS if self._hover else self.DOT_RADIUS
        center = self.rect().center()
        if self._port.is_inout():
            radius *= self.SHAPE_SCALE
            points = [(0, -radius), (radius, 0), (0, radius), (-radius, 0)]
        elif self._arrow:
            radius *= self.SHAPE_SCALE
            inward = 1 if center.x() < self._parent_rect_item().rect().center().x() else -1
            # The way the arrow points, and where its tip is from the border
            direction = inward if self._port.is_input() else -inward
            # An output reaches as far out as the diamond of an inout port
            inside = self.INPUT_INSIDE if self._port.is_input() else 0.5
            tip = direction * inside * 2 * radius
            base = tip - direction * 2 * radius
            points = [(tip, 0), (base, -radius), (base, radius)]
        else:
            painter.drawEllipse(center, radius, radius)
            return
        painter.drawPolygon(QPolygonF([center + QPointF(x, y) for x, y in points]))

    def boundingRect(self) -> QRectF:
        """
        QT function. An arrow or a diamond can be larger than the rect, when hovered: it is
        all repainted when the hover ends, or a part of it is left.
        """
        rect = super().boundingRect()
        # Qt can ask while the item is created, before it has a port
        port = getattr(self, "_port", None)
        if port is None or (not self._arrow and not port.is_inout()):
            return rect
        # The tip of a hovered input arrow is the farthest from the center, plus antialiasing
        extent = 2 * self.HOVER_RADIUS * self.SHAPE_SCALE * self.INPUT_INSIDE + 1
        margin = max(0.0, extent - min(rect.width(), rect.height()) / 2)
        return rect.adjusted(-margin, -margin, margin, margin)

    @property
    def port(self) -> Port:
        """The port of the item"""
        return self._port

    def _repaint(self) -> None:
        """Make scene repaint for component update"""
        self._app_model.sig_repaint.emit()

    def mousePressEvent(self, _: QGraphicsSceneMouseEvent) -> None:
        """QT event callback function"""
        if self._app_model.is_running:
            return
        if self._app_model.objects.new_wire.ongoing():
            try:
                self._app_model.objects.new_wire.end(self._port.parent(), self._port.name())
            except PortConnectionError as exc:
                self._app_model.objects.new_wire.abort()
                self._app_model.sig_error.emit(str(exc))
                self._repaint()
        else:
            self._app_model.objects.new_wire.start(self._port.parent(), self._port.name())

    def hoverEnterEvent(self, _: QGraphicsSceneHoverEvent) -> None:
        """QT event callback function"""
        if self._app_model.is_running:
            return
        self._hover = True
        self.update()
        self.setCursor(Qt.CursorShape.CrossCursor)

    def hoverLeaveEvent(self, _: QGraphicsSceneHoverEvent) -> None:
        """QT event callback function"""
        if self._app_model.is_running:
            return
        self._hover = False
        self.update()
        self.setCursor(Qt.CursorShape.ArrowCursor)

    def _parent_rect_item(self) -> QGraphicsRectItem:
        parent = self.parentItem()
        assert isinstance(parent, QGraphicsRectItem)
        return parent

    def portParentRect(self) -> QRectF:
        """The rect of the component that the port belongs to, in scene coordinates"""
        parent = self._parent_rect_item()
        return parent.rect().translated(parent.pos())

    def portPos(self) -> QPointF:
        """The center of the port, in scene coordinates"""
        return self._parent_rect_item().pos() + self.rect().center()
