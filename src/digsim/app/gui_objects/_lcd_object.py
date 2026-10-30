# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""An HD44780 16x2 LCD module placed in the GUI"""

from __future__ import annotations

import typing
from typing import TYPE_CHECKING

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QRadialGradient

from digsim.app._wire_route import rotated
from digsim.circuit.components import HD44780
from digsim.circuit.components.atoms import Component, Port

from . import _theme as theme
from ._component_object import ComponentObject


if TYPE_CHECKING:
    from digsim.app.model import AppModel


class _Backlight(typing.NamedTuple):
    """The colors of a backlight: the glass, and a pixel that is on"""

    glass: QColor
    pixel: QColor


BACKLIGHTS = {
    "green": _Backlight(QColor("#a6c93b"), QColor("#1f2b10")),
    "blue": _Backlight(QColor("#2357e0"), QColor("#eef3ff")),
    "amber": _Backlight(QColor("#f0a21c"), QColor("#3a2006")),
    "white": _Backlight(QColor("#e6eaec"), QColor("#1c2026")),
    "red": _Backlight(QColor("#e0353a"), QColor("#2c0606")),
}

PCB = QColor("#1d6b3a")
COPPER = QColor("#d4b25c")
SILKSCREEN = QColor("#f2f5f2")
BEZEL = QColor("#26292c")

# The pins of the module, left to right: the ports have the names of the pins
PINS = ["VSS", "VDD", "V0", "RS", "RW", "E", *(f"D{bit}" for bit in range(8)), "A", "K"]


class LcdObject(ComponentObject):
    """
    A 16x2 LCD module, drawn to scale (2.54 mm is 10 pixels): the board with the pins at
    the top and their names, the bezel and the display with its 5x8 dot characters in the
    color of the backlight. The pins for the power, the contrast and the backlight are
    not connected.
    """

    SHOW_PORT_NAMES = False
    WIDTH = 320
    HEIGHT = 144
    PIN_DISTANCE = 10
    # The first pin, and the row of pins from the top
    PIN1_X = 30
    PIN_Y = 8
    BEZEL = QRectF(20, 36, 280, 94)
    VIEW = QRectF(33, 51, 254, 64)
    # A dot, and the distance from one to the next, a character, and from one line to the next
    DOT = (2.1, 2.5)
    DOT_PITCH = (2.36, 2.76)
    CHARACTER_PITCH = 14.0
    LINE_PITCH = 23.4

    def __init__(
        self, app_model: AppModel, component: Component, xpos: float, ypos: float
    ) -> None:
        super().__init__(app_model, component, xpos, ypos, port_distance=self.PIN_DISTANCE)

    @property
    def component(self) -> HD44780:
        component = self._component
        assert isinstance(component, HD44780)
        return component

    def update_ports(self) -> None:
        """The ports are pins at the top"""
        self.width = self.WIDTH
        self.height = self.HEIGHT
        top_left = self.object_pos
        for port in self._component.ports:
            x = top_left.x() + self.PIN1_X + PINS.index(port.name()) * self.PIN_DISTANCE
            rect = QRectF(
                x - self.PORT_SIDE / 2,
                top_left.y() - self.RECT_TO_BORDER,
                self.PORT_SIDE,
                self.PORT_SIDE,
            )
            self.set_port_rect(port, rect)
        self._apply_rotation()

    def port_direction(self, port: Port) -> str:
        return rotated("up", self._rotation)

    @classmethod
    def paint_module(
        cls,
        painter: QPainter,
        rect: QRectF,
        pixels: list[list[tuple[int, ...]]],
        backlight: str,
        selected: bool,
        connected: list[bool],
    ) -> None:
        """The board, the pins (connected is True for a pin with a port), the display"""
        painter.save()
        painter.translate(rect.topLeft())
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        board = QRectF(0, 0, rect.width(), rect.height())
        painter.setPen(theme.outline_pen(True) if selected else Qt.PenStyle.NoPen)
        painter.setBrush(PCB)
        painter.drawRoundedRect(board, 3, 3)
        cls._paint_holes(painter, board)
        cls._paint_pins(painter, connected)
        cls._paint_bezel(painter)
        cls._paint_display(painter, pixels, BACKLIGHTS.get(backlight, BACKLIGHTS["green"]))
        theme.paint_text(
            painter,
            QRectF(cls.BEZEL.left(), cls.BEZEL.bottom() + 2, 120, 10),
            "HD44780  16x2",
            5,
            SILKSCREEN,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        )
        painter.restore()

    @classmethod
    def _paint_holes(cls, painter: QPainter, board: QRectF) -> None:
        """The mounting holes in the corners"""
        inset = 9.0
        for x in (inset, board.width() - inset):
            for y in (inset, board.height() - inset):
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(COPPER)
                painter.drawEllipse(QPointF(x, y), 6.0, 6.0)
                painter.setBrush(theme.BACKGROUND)
                painter.drawEllipse(QPointF(x, y), 4.5, 4.5)

    @classmethod
    def _paint_pins(cls, painter: QPainter, connected: list[bool]) -> None:
        """The pads of the pins, a track from each port to its pad, and the pin names"""
        for index, name in enumerate(PINS):
            x = cls.PIN1_X + index * cls.PIN_DISTANCE
            if connected[index]:
                painter.setPen(theme.ink_pen(1.6, COPPER))
                painter.drawLine(QPointF(x, 0), QPointF(x, cls.PIN_Y))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(COPPER)
            pad = QRectF(0, 0, 7, 7)
            pad.moveCenter(QPointF(x, cls.PIN_Y))
            if index == 0:
                # Pin 1 has a square pad
                painter.drawRect(pad)
            else:
                painter.drawEllipse(pad)
            painter.setBrush(QColor("#2b2f2b"))
            painter.drawEllipse(QPointF(x, cls.PIN_Y), 1.6, 1.6)
            painter.save()
            painter.translate(x, cls.PIN_Y + 5)
            painter.rotate(-90)
            theme.paint_text(
                painter,
                QRectF(-20, -4, 19, 8),
                name,
                5,
                SILKSCREEN,
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            )
            painter.restore()

    @classmethod
    def _paint_bezel(cls, painter: QPainter) -> None:
        """The metal frame around the display"""
        gradient = QLinearGradient(cls.BEZEL.topLeft(), cls.BEZEL.bottomLeft())
        gradient.setColorAt(0, BEZEL.lighter(140))
        gradient.setColorAt(0.08, BEZEL)
        gradient.setColorAt(1, BEZEL.darker(130))
        painter.setPen(theme.ink_pen(0.8, QColor("#111314")))
        painter.setBrush(gradient)
        painter.drawRoundedRect(cls.BEZEL, 2, 2)
        # The tabs that hold the frame to the board
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(BEZEL.lighter(120))
        for x in (cls.BEZEL.left() + 40, cls.BEZEL.right() - 52):
            painter.drawRect(QRectF(x, cls.BEZEL.bottom() - 2, 12, 4))

    @classmethod
    def _paint_display(
        cls, painter: QPainter, pixels: list[list[tuple[int, ...]]], backlight: _Backlight
    ) -> None:
        """The glass, lit by the backlight, and the dots of the characters"""
        glow = QRadialGradient(cls.VIEW.center(), cls.VIEW.width() * 0.6)
        glow.setColorAt(0, backlight.glass.lighter(112))
        glow.setColorAt(1, backlight.glass.darker(108))
        painter.setPen(theme.ink_pen(1.0, backlight.glass.darker(150)))
        painter.setBrush(glow)
        painter.drawRect(cls.VIEW)
        off = theme.dim(backlight.pixel, 0.05, backlight.glass)
        dot_width, dot_height = cls.DOT
        pitch_x, pitch_y = cls.DOT_PITCH
        columns = len(pixels[0])
        text_width = (columns - 1) * cls.CHARACTER_PITCH + 4 * pitch_x + dot_width
        text_height = cls.LINE_PITCH + 7 * pitch_y + dot_height
        left = cls.VIEW.center().x() - text_width / 2
        top = cls.VIEW.center().y() - text_height / 2
        for row, line in enumerate(pixels):
            for column, glyph in enumerate(line):
                x0 = left + column * cls.CHARACTER_PITCH
                y0 = top + row * cls.LINE_PITCH
                for dot_row, bits in enumerate(glyph):
                    for dot in range(5):
                        lit = bits & (0x10 >> dot)
                        painter.fillRect(
                            QRectF(
                                x0 + dot * pitch_x, y0 + dot_row * pitch_y, dot_width, dot_height
                            ),
                            backlight.pixel if lit else off,
                        )

    def paint_component(self, painter: QPainter) -> None:
        names = {port.name() for port in self.component.ports}
        self.paint_module(
            painter,
            QRectF(self.rect()),
            self.component.pixels(),
            self.component.backlight,
            self.selected,
            [name in names for name in PINS],
        )

    @classmethod
    def paint_selectable_component(cls, painter: QPainter, size: QSize, name: str) -> None:
        def line(text: str) -> list[tuple[int, ...]]:
            return [HD44780.rom_glyph(ord(char)) for char in text.ljust(16)]

        pixels = [line(" Hello"), line(" World")]
        connected = [pin not in ("VSS", "VDD", "V0", "A", "K") for pin in PINS]
        scale = (size.width() - 6) / cls.WIDTH
        painter.save()
        painter.translate(3, size.width() / 2 - 2 - cls.HEIGHT * scale / 2)
        painter.scale(scale, scale)
        cls.paint_module(
            painter, QRectF(0, 0, cls.WIDTH, cls.HEIGHT), pixels, "green", False, connected
        )
        painter.restore()
        cls.paint_selectable_component_name(painter, QPointF(0, 0), size, name)
