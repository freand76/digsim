# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPen
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsRectItem,
)


class WireSegmentObject(QGraphicsRectItem):
    CLOSE_TO_WIRE_MARGIN = 10

    def __init__(self, app_model, net_name, parent, end, sink_port):
        self._end = QPointF(end.x(), end.y()) if end is not None else None
        self._sink_port = sink_port
        self._parent = parent
        super().__init__(self.get_rect(self._parent.point(), self.point()))
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self._app_model = app_model
        self._net_name = net_name
        _, self._src_port = self._app_model.objects.circuit.net_name_to_component_port(net_name)
        self._selected = False
        self._parent_widget = None
        self._children = []
        pen = QPen(QColor("red"))
        pen.setWidth(2)
        self.setPen(pen)

    def set_parent_widget(self, parent):
        """Set the parent"""
        self._parent_widget = parent

    def add_child(self, child):
        self._children.append(child)

    def repaint(self):
        """Update GUI for this component object"""
        self._app_model.sig_repaint.emit()

    def update_y(self, y):
        if self._end is not None:
            self._end.setY(y)
        else:
            self._parent.point().setY(y)
        self.setRect(self.get_rect(self._parent.point(), self.point()))

    def get_rect(self, start, end):
        x_low = min(start.x(), end.x())
        x_high = max(start.x(), end.x())
        y_low = min(start.y(), end.y())
        y_high = max(start.y(), end.y())
        return QRectF(
            x_low - self.CLOSE_TO_WIRE_MARGIN,
            y_low - self.CLOSE_TO_WIRE_MARGIN,
            x_high - x_low + 2 * self.CLOSE_TO_WIRE_MARGIN,
            y_high - y_low + 2 * self.CLOSE_TO_WIRE_MARGIN,
        )

    def select(self, selected):
        self._selected = selected
        self._parent.select(selected)
        self.repaint()

    def itemChange(self, change, value):
        """QT function"""
        if change == QGraphicsItem.ItemSelectedHasChanged:
            self.select(self.isSelected())
        return super().itemChange(change, value)

    def point(self):
        return self._sink_port.point() if self._sink_port is not None else self._end

    def _get_wire_color(self):
        port_value = self._src_port.value
        if port_value == "X":
            return Qt.red
        if port_value == 0:
            return Qt.darkGray

        max_value = 2**self._src_port.width - 1
        # Start with dark gray
        green = 128
        # Calculate the green component, ranging from 128 to 255
        green += int(127 * port_value / max_value)
        return QColor(128, green, 128)

    def paint(self, painter, option, widget=None):
        """QT function"""
        pen = QPen(Qt.darkGray)
        if self._src_port.width > 1:
            pen.setWidth(4)
        else:
            pen.setWidth(2)

        if not self._app_model.is_running and self._selected:
            pen.setColor(Qt.black)
        elif self._app_model.settings.get("color_wires"):
            pen.setColor(self._get_wire_color())

        painter.setPen(pen)
        painter.drawLine(self._parent.point(), self.point())
