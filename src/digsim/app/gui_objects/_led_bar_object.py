# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""A LED bar component placed in the GUI"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QPoint, QSize, Qt
from PySide6.QtGui import QPainter

from digsim.circuit.components import LedBar
from digsim.circuit.components.atoms import Component

from ._component_object import ComponentObject


if TYPE_CHECKING:
    from digsim.app.model import AppModel


class LedBarObject(ComponentObject):
    """The class for a LED bar component placed in the GUI"""

    LED_WIDTH = 8
    LED_HEIGHT = 24
    LED_GAP = 4

    def __init__(
        self, app_model: AppModel, component: Component, xpos: float, ypos: float
    ) -> None:
        super().__init__(app_model, component, xpos, ypos)
        self.update_size()

    @property
    def component(self) -> LedBar:
        component = self._component
        assert isinstance(component, LedBar)
        return component

    def update_size(self) -> None:
        leds = len(self.component.lit())
        self.width = 2 * self.inport_x_pos() + 40 + leds * (self.LED_WIDTH + self.LED_GAP)
        self.update_ports()

    def paint_component(self, painter: QPainter) -> None:
        self.paint_component_base(painter)
        self.paint_component_name(painter)
        # Draw the most significant bit to the left
        xpos = int(self.object_pos.x() + self.inport_x_pos() + 30)
        ypos = int(self.object_pos.y() + self.height / 2 - self.LED_HEIGHT / 2 + 8)
        for led_on in reversed(self.component.lit()):
            self._paint_led(painter, xpos, ypos, led_on)
            xpos += self.LED_WIDTH + self.LED_GAP

    @classmethod
    def _paint_led(cls, painter: QPainter, xpos: int, ypos: int, led_on: bool) -> None:
        painter.setPen(Qt.GlobalColor.black)
        painter.setBrush(Qt.GlobalColor.red if led_on else Qt.GlobalColor.darkRed)
        painter.drawRect(xpos, ypos, cls.LED_WIDTH, cls.LED_HEIGHT)

    @classmethod
    def paint_selectable_component(cls, painter: QPainter, size: QSize, name: str) -> None:
        xpos = (size.width() - 6 * (cls.LED_WIDTH + cls.LED_GAP)) // 2
        for led_on in [True, False, True, True, False, False]:
            cls._paint_led(painter, xpos, 20, led_on)
            xpos += cls.LED_WIDTH + cls.LED_GAP
        cls.paint_selectable_component_name(painter, QPoint(0, 0), size, name)
