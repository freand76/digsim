# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""A LED bar component placed in the GUI"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QPointF, QRectF, QSize
from PySide6.QtGui import QPainter

from digsim.circuit.components import LedBar
from digsim.circuit.components.atoms import Component

from . import _theme as theme
from ._component_object import ComponentObject
from ._symbol_objects import paint_icon, port_dots


if TYPE_CHECKING:
    from digsim.app.model import AppModel


class LedBarObject(ComponentObject):
    """A LED bar: a display window with an LED next to each input, LED 0 at the top"""

    SHOW_PORT_NAMES = False
    LED_WIDTH = 18
    LED_HEIGHT = 6
    # From one LED to the next, and from one input to the next
    LED_DISTANCE = 10
    # From the body to the window, and from the window to the LEDs
    MARGIN = 5
    WINDOW_MARGIN = 3
    # On the 10 pixels between the ports of the other components
    BORDER_TO_PORT = 10

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
        self.width = self.LED_WIDTH + 2 * (self.MARGIN + self.WINDOW_MARGIN)
        self.height = (leds - 1) * self.LED_DISTANCE + 2 * self.BORDER_TO_PORT
        self.update_ports()

    @classmethod
    def paint_leds(
        cls, painter: QPainter, rect: QRectF, ys: list[float], lit: list[bool], color: str
    ) -> None:
        """The window and an LED at each y"""
        theme.paint_window(
            painter, rect.adjusted(cls.MARGIN, cls.MARGIN, -cls.MARGIN, -cls.MARGIN)
        )
        for y, on in zip(ys, lit, strict=True):
            led = QRectF(0, 0, cls.LED_WIDTH, cls.LED_HEIGHT)
            led.moveCenter(QPointF(rect.center().x(), y))
            theme.paint_bar_led(painter, led, theme.led_color(color), on)

    def paint_component(self, painter: QPainter) -> None:
        self.paint_component_base(painter)
        ys = [self.get_port_item(port).rect().center().y() for port in self.component.inports()]
        self.paint_leds(
            painter, QRectF(self.rect()), ys, self.component.lit(), self.component.color
        )

    @classmethod
    def paint_selectable_component(cls, painter: QPainter, size: QSize, name: str) -> None:
        leds = [True, False, True, True, False, False]
        height = (len(leds) - 1) * cls.LED_DISTANCE + 2 * cls.BORDER_TO_PORT

        def paint(rect: QRectF) -> None:
            theme.paint_body(painter, rect)
            ys = [rect.top() + cls.BORDER_TO_PORT + cls.LED_DISTANCE * idx for idx in range(6)]
            cls.paint_leds(painter, rect, ys, leds, "red")
            port_dots(painter, [QPointF(rect.left() - 1, y) for y in ys])

        width = cls.LED_WIDTH + 2 * (cls.MARGIN + cls.WINDOW_MARGIN)
        paint_icon(painter, size, (width, height), paint, scale=0.9)
        cls.paint_selectable_component_name(painter, QPointF(0, 0), size, name)
