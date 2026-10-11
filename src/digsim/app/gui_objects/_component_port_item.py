# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""A component port graphics item"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QPointF, QRect, QRectF, Qt
from PySide6.QtGui import QBrush, QPen
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsRectItem,
    QGraphicsSceneHoverEvent,
    QGraphicsSceneMouseEvent,
)

from digsim.circuit.components.atoms import Port, PortConnectionError


if TYPE_CHECKING:
    from digsim.app.model import AppModel


class PortGraphicsItem(QGraphicsRectItem):
    """A port graphics item"""

    def __init__(self, app_model: AppModel, parent: QGraphicsItem, port: Port) -> None:
        super().__init__(QRect(0, 0, 0, 0), parent)
        self._app_model = app_model
        self._port = port
        self.setPen(QPen(Qt.GlobalColor.black))
        self.setBrush(Qt.BrushStyle.SolidPattern)
        self.setBrush(QBrush(Qt.GlobalColor.gray))
        self.setAcceptHoverEvents(True)

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
        self.setBrush(QBrush(Qt.GlobalColor.black))
        self.setCursor(Qt.CursorShape.CrossCursor)

    def hoverLeaveEvent(self, _: QGraphicsSceneHoverEvent) -> None:
        """QT event callback function"""
        if self._app_model.is_running:
            return
        self.setBrush(QBrush(Qt.GlobalColor.gray))
        self.setCursor(Qt.CursorShape.ArrowCursor)

    def _parent_rect_item(self) -> QGraphicsRectItem:
        parent = self.parentItem()
        assert isinstance(parent, QGraphicsRectItem)
        return parent

    def portParentRect(self) -> QRectF:
        """return the parent rect"""
        parent = self._parent_rect_item()
        return parent.rect().translated(parent.pos())

    def portPos(self) -> QPointF:
        """return the parent position"""
        return self._parent_rect_item().pos() + self.rect().center()
