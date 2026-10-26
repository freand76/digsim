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
    A port graphics item, drawn as a dot in its rect (the rect is where it is clicked). An
    inout port, which both drives its wire and reads it, is a diamond.
    """

    DOT_RADIUS = 2.5
    HOVER_RADIUS = 4.0

    def __init__(self, app_model: AppModel, parent: QGraphicsItem, port: Port) -> None:
        super().__init__(QRect(0, 0, 0, 0), parent)
        self._app_model = app_model
        self._port = port
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
            radius *= 1.6
            painter.drawPolygon(
                QPolygonF(
                    [
                        center + QPointF(0, -radius),
                        center + QPointF(radius, 0),
                        center + QPointF(0, radius),
                        center + QPointF(-radius, 0),
                    ]
                )
            )
            return
        painter.drawEllipse(center, radius, radius)

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
