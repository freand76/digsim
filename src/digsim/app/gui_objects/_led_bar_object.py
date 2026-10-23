# Copyright (c) Fredrik Andersson, 2023-2026
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
    """The class for a LED bar component placed in the GUI, drawn like a DIP switch"""

    SHOW_PORT_NAMES = False
    LED_WIDTH = 24
    LED_HEIGHT = 8
    # From one LED to the next, and from one input to the next
    LED_DISTANCE = 10
    # The frame around the LEDs
    FRAME = 10
    # From the top to the first input, the frame and half an LED
    BORDER_TO_PORT = FRAME + LED_HEIGHT // 2

    def __init__(
        self, app_model: AppModel, component: Component, xpos: float, ypos: float
    ) -> None:
        super().__init__(app_model, component, xpos, ypos, port_distance=self.LED_DISTANCE)
        self.update_size()

    @property
    def component(self) -> LedBar:
        component = self._component
        assert isinstance(component, LedBar)
        return component

    def update_size(self) -> None:
        leds = len(self.component.lit())
        self.width = self.LED_WIDTH + 2 * self.FRAME
        self.height = (leds - 1) * self.LED_DISTANCE + 2 * self.BORDER_TO_PORT
        self.update_ports()

    def paint_component(self, painter: QPainter) -> None:
        self.paint_component_base(painter, color=Qt.GlobalColor.black)
        # Each LED next to its input, LED 0 at the top
        xpos = int(self.object_pos.x() + self.width / 2 - self.LED_WIDTH / 2)
        ypos = int(self.object_pos.y() + self.BORDER_TO_PORT - self.LED_HEIGHT / 2)
        for led_on in self.component.lit():
            self._paint_led(painter, xpos, ypos, led_on)
            ypos += self.LED_DISTANCE

    @classmethod
    def _paint_led(cls, painter: QPainter, xpos: int, ypos: int, led_on: bool) -> None:
        painter.setPen(Qt.GlobalColor.darkGray)
        painter.setBrush(Qt.GlobalColor.red if led_on else Qt.GlobalColor.darkRed)
        painter.drawRect(xpos, ypos, cls.LED_WIDTH, cls.LED_HEIGHT)

    @classmethod
    def paint_selectable_component(cls, painter: QPainter, size: QSize, name: str) -> None:
        leds = [True, False, True, True, False, False]
        xpos = (size.width() - cls.LED_WIDTH) // 2
        ypos = (size.width() - len(leds) * cls.LED_DISTANCE) // 2
        painter.setPen(Qt.GlobalColor.black)
        painter.setBrush(Qt.GlobalColor.black)
        painter.drawRoundedRect(
            xpos - cls.FRAME,
            ypos - cls.FRAME,
            cls.LED_WIDTH + 2 * cls.FRAME,
            (len(leds) - 1) * cls.LED_DISTANCE + cls.LED_HEIGHT + 2 * cls.FRAME,
            5,
            5,
        )
        for led_on in leds:
            cls._paint_led(painter, xpos, ypos, led_on)
            ypos += cls.LED_DISTANCE
        cls.paint_selectable_component_name(painter, QPoint(0, 0), size, name)
