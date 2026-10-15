# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""A hexdigit component placed in the GUI"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QPoint, QPointF, QRect, Qt
from PySide6.QtGui import QFont, QPainter, QPen
from PySide6.QtWidgets import QStyleOptionGraphicsItem, QWidget

from digsim.circuit.components import DipSwitch
from digsim.circuit.components.atoms import Component

from ._image_objects import ImageObject


if TYPE_CHECKING:
    from digsim.app.model import AppModel


class DipSwitchObject(ImageObject):
    """The class for a DIP switch component placed in the GUI"""

    IMAGE_FILENAME = "images/DIP_SWITCH.png"
    DIP_SWITCH_WIDTH = 20
    DIP_SWITCH_HEIGHT = 10

    _DIP_SWITCH_FONT = QFont("Arial", 8)

    def __init__(
        self, app_model: AppModel, component: Component, xpos: float, ypos: float
    ) -> None:
        super().__init__(app_model, component, xpos, ypos, port_distance=self.DIP_SWITCH_HEIGHT)
        self.width = 2.5 * self.DIP_SWITCH_WIDTH
        self.height = self.component.bits() * self.DIP_SWITCH_HEIGHT
        self._rects: list[QRect] = []
        self.update_ports()

    @property
    def component(self) -> DipSwitch:
        component = self._component
        assert isinstance(component, DipSwitch)
        return component

    def update_ports(self) -> None:
        super().update_ports()
        self._rects = []
        for idx in range(self.component.bits()):
            port_pos = self.get_port_pos(f"{idx}")
            self._rects.append(
                QRect(
                    int(self.object_pos.x() + self.rect().width() / 2 - self.DIP_SWITCH_WIDTH / 2),
                    int(port_pos.y() - self.DIP_SWITCH_HEIGHT / 2),
                    self.DIP_SWITCH_WIDTH,
                    self.DIP_SWITCH_HEIGHT,
                )
            )

    def mouse_position(self, pos: QPointF) -> None:
        """update component according to on mouse move"""
        select = None
        pos = pos - self.pos()
        for idx, rect in enumerate(self._rects):
            if (
                pos.x() > rect.x()
                and pos.x() < (rect.x() + rect.width())
                and pos.y() > rect.y()
                and pos.y() < (rect.y() + rect.height())
            ):
                select = idx
                break
        # Repaint only when another switch is highlighted, not on every mouse move
        if select != self.component.selected():
            self.component.select(select)
            self.repaint()

    def single_click_action(self) -> None:
        self.component.toggle()
        self.repaint()

    def _paint_dip_switch(self, painter: QPainter) -> None:
        pen = QPen()
        pen.setColor(Qt.GlobalColor.black)
        pen.setWidth(1)
        painter.setPen(pen)
        select_id = self.component.selected()
        for idx, rect in enumerate(self._rects):
            painter.setBrush(Qt.GlobalColor.darkGray)
            painter.drawRect(rect)
            if select_id == idx:
                painter.setBrush(Qt.GlobalColor.green)
            else:
                painter.setBrush(Qt.GlobalColor.white)
            if self.component.is_set(idx):
                painter.drawRect(
                    int(rect.x() + rect.width() / 2 + 1),
                    rect.y() + 1,
                    int(rect.width() / 2 - 2),
                    rect.height() - 2,
                )
            else:
                painter.drawRect(
                    rect.x() + 1, rect.y() + 1, int(rect.width() / 2 - 2), rect.height() - 2
                )
        painter.setFont(self._DIP_SWITCH_FONT)
        painter.setPen(Qt.GlobalColor.white)
        for idx, rect in enumerate(self._rects):
            port_str = f"{idx + 1}"
            str_pixels_w, _ = self.get_string_metrics(port_str, self._DIP_SWITCH_FONT)
            painter.drawText(
                QPoint(rect.x() - str_pixels_w - 4, rect.y() + rect.height() - 1), port_str
            )

        _, str_h = self.get_string_metrics("ON", self._DIP_SWITCH_FONT)
        painter.drawText(
            int(self.rect().x() + self.rect().width() / 2),
            int(self.rect().y() + self.BORDER_TO_PORT - str_h),
            "ON",
        )

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        """QT function"""
        self.paint_component_base(painter, color=Qt.GlobalColor.red)
        self._paint_dip_switch(painter)
