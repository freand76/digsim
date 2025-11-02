# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""A component port graphics item"""

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QBrush, QPen
from PySide6.QtWidgets import QGraphicsRectItem

from digsim.circuit.components.atoms import PortConnectionError


class PortGraphicsItem(QGraphicsRectItem):
    """A port graphics item"""

    def __init__(self, app_model, parent, port):
        super().__init__(QRect(0, 0, 0, 0), parent)
        self._app_model = app_model
        self._port = port
        self.setPen(QPen(Qt.black))
        self.setBrush(Qt.SolidPattern)
        self.setBrush(QBrush(Qt.gray))
        self.setAcceptHoverEvents(True)

    def _repaint(self):
        """Make scene repaint for component update"""
        self._app_model.sig_repaint.emit()

    def mousePressEvent(self, _):
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

    def hoverEnterEvent(self, _):
        """QT event callback function"""
        if self._app_model.is_running:
            return
        self.setBrush(QBrush(Qt.black))
        self.setCursor(Qt.CrossCursor)

    def hoverLeaveEvent(self, _):
        """QT event callback function"""
        if self._app_model.is_running:
            return
        self.setBrush(QBrush(Qt.gray))
        self.setCursor(Qt.ArrowCursor)

    def portParentRect(self):
        """return the parent rect"""
        return self.parentItem().rect().translated(self.parentItem().pos())

    def portPos(self):
        """return the parent position"""
        return self.parentItem().pos() + self.rect().center()
