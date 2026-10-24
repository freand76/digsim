# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""A 7-segment component placed in the GUI"""

from __future__ import annotations

import typing
from typing import TYPE_CHECKING

from PySide6.QtCore import QPoint, QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QPainter, QPainterPath

from digsim.circuit.components import HexDigit, SevenSegment
from digsim.circuit.components.atoms import Component

from . import _theme as theme
from ._component_object import ComponentObject


if TYPE_CHECKING:
    from digsim.app.model import AppModel


class SevenSegmentObject(ComponentObject):
    """
    A 7-segment digit: the display without a body, a lead from each input to it with the
    name of the input on it
    """

    SHOW_PORT_NAMES = False
    # From the display to the digits
    DISPLAY_MARGIN = 6

    SEGMENT_TYPE_AND_POS: typing.ClassVar[dict[str, tuple[str, QPoint]]] = {
        "A": ("H", QPoint(3, 0)),
        "B": ("V", QPoint(31, 3)),
        "C": ("V", QPoint(31, 33)),
        "D": ("H", QPoint(3, 61)),
        "E": ("V", QPoint(0, 33)),
        "F": ("V", QPoint(0, 3)),
        "G": ("H", QPoint(3, 31)),
    }

    SEGMENT_CORDS: typing.ClassVar[dict[str, list[QPoint]]] = {
        "V": [
            QPoint(3, 3),
            QPoint(3, 20),
            QPoint(0, 25),
            QPoint(-3, 20),
            QPoint(-3, 3),
            QPoint(0, 0),
        ],
        "H": [
            QPoint(3, 3),
            QPoint(20, 3),
            QPoint(25, 0),
            QPoint(20, -3),
            QPoint(3, -3),
            QPoint(0, 0),
        ],
    }

    PORT_TO_RECT_MARGIN = 5
    RECT_TO_DIGIT_RECT_MARGIN = 5
    DIGIT_RECT_TO_DIGIT_MARGIN = 10
    DIGIT_WIDTH = 54
    DIGIT_HEIGHT = 80

    # The digits are drawn smaller than the sizes above
    SCALE = 0.75

    DOT_OFFSET_X = 40
    DOT_OFFSET_Y = 60
    DOT_RADIUS = 3

    def __init__(
        self,
        app_model: AppModel,
        component: Component,
        xpos: float,
        ypos: float,
        port_distance: int = 10,
    ) -> None:
        super().__init__(app_model, component, xpos, ypos, port_distance=port_distance)
        self.setup_size()

    @property
    def component(self) -> SevenSegment | HexDigit:
        component = self._component
        assert isinstance(component, (SevenSegment, HexDigit))
        return component

    def lead_length(self) -> float:
        """From the inputs to the display: room for the names of the inputs"""
        longest = max((self._port_names[port] for port in self.component.inports()), key=len)
        text_width, _ = self.get_string_metrics(longest, theme.font(6))
        return text_width + 10

    def setup_size(self) -> None:
        """Setup the size of the component"""
        self.digit_left = self.lead_length()
        self.width = self.digit_left + self.DIGIT_WIDTH * self.SCALE + 2 * self.DISPLAY_MARGIN
        self.update_ports()

    def paint_display(self, painter: QPainter, segments: list[str]) -> None:
        """The leads with the names of the inputs, the display and its digits"""
        rect = QRectF(self.rect())
        display = QRectF(rect.left() + self.digit_left, rect.top(), 0, rect.height())
        display.setRight(rect.right())
        for port in self.component.inports():
            y = self.get_port_item(port).rect().center().y()
            width = 3.0 if port.width > 1 else theme.LINE_WIDTH
            theme.lead(painter, QPointF(rect.left() - 1, y), QPointF(display.left(), y), width)
            theme.paint_text(
                painter,
                QRectF(rect.left() + 4, y - 9, self.digit_left - 6, 8),
                self._port_names[port],
                6,
                theme.MUTED,
                Qt.AlignmentFlag.AlignLeft,
            )
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(theme.outline_pen(self.selected))
        painter.setBrush(theme.DISPLAY)
        painter.drawRoundedRect(display, theme.CORNER, theme.CORNER)
        digits_width = len(segments) * self.DIGIT_WIDTH * self.SCALE
        self.paint_digits(
            painter,
            QPointF(
                display.center().x() - digits_width / 2,
                display.center().y() - self.DIGIT_HEIGHT * self.SCALE / 2,
            ),
            segments,
        )

    def paint_component(self, painter: QPainter) -> None:
        self.paint_display(painter, [self.component.segments()])

    @classmethod
    def paint_digits(cls, painter: QPainter, pos: QPointF, segments: list[str]) -> None:
        """The window and the digits in it, at SCALE, from the top left corner"""
        painter.save()
        painter.translate(pos)
        painter.scale(cls.SCALE, cls.SCALE)
        cls.paint_digit_rect(painter, 0, 0, len(segments))
        for index, active_segments in enumerate(segments):
            cls.draw_digit(painter, index * cls.DIGIT_WIDTH, 0, active_segments)
        painter.restore()

    @classmethod
    def paint_selectable_component(cls, painter: QPainter, size: QSize, name: str) -> None:
        # An input for each segment and the dot
        leads = [(5.0 + 10 * idx, False) for idx in range(8)]
        cls.paint_selectable_digit(painter, size, name, "ADEFG", leads)

    @classmethod
    def paint_selectable_digit(
        cls,
        painter: QPainter,
        size: QSize,
        name: str,
        segments: str,
        leads: list[tuple[float, bool]],
    ) -> None:
        """Paint a digit (for the component selector), with a lead at each (y, is a bus)"""
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.translate(size.width() / 2 + 6, 10)
        painter.scale(0.58, 0.58)
        xpos = -cls.DIGIT_WIDTH / 2
        for y, bus in leads:
            theme.lead(painter, QPointF(xpos - 34, y), QPointF(xpos - 6, y), 5.0 if bus else 2.5)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(theme.INK)
            painter.drawEllipse(QPointF(xpos - 34, y), 3.5, 3.5)
        painter.setPen(theme.ink_pen(2.5))
        painter.setBrush(theme.DISPLAY)
        painter.drawRoundedRect(
            QRectF(xpos - 6, -4, cls.DIGIT_WIDTH + 12, cls.DIGIT_HEIGHT + 8), 6, 6
        )
        cls.draw_digit(painter, xpos, 0, segments)
        painter.restore()
        cls.paint_selectable_component_name(painter, QPoint(0, 0), size, name)

    @classmethod
    def paint_digit_rect(
        cls, painter: QPainter, xpos: float, ypos: float, digits: int = 1
    ) -> None:
        """Paint the digit background"""
        theme.paint_window(painter, QRectF(xpos, ypos, cls.DIGIT_WIDTH * digits, cls.DIGIT_HEIGHT))

    @classmethod
    def draw_digit(cls, painter: QPainter, xpos: float, ypos: float, active_segments: str) -> None:
        """Paint the LED digit segments"""
        start_point = QPoint(
            int(xpos + cls.DIGIT_RECT_TO_DIGIT_MARGIN), int(ypos + cls.DIGIT_RECT_TO_DIGIT_MARGIN)
        )
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        lit = theme.led_color("red")
        unlit = theme.dim(lit, 0.16, theme.DISPLAY)
        for seg, type_pos in cls.SEGMENT_TYPE_AND_POS.items():
            color = lit if seg in active_segments else unlit
            painter.setPen(theme.ink_pen(1.0, color))
            painter.setBrush(color)
            pos_vector = cls.SEGMENT_CORDS[type_pos[0]]
            offset = type_pos[1]
            path = QPainterPath()
            path.moveTo(offset + start_point)
            for point in pos_vector:
                path.lineTo(offset + point + start_point)
            path.closeSubpath()
            painter.drawPath(path)

        color = lit if "." in active_segments else unlit
        painter.setPen(theme.ink_pen(1.0, color))
        painter.setBrush(color)
        dot_point = QPoint(cls.DOT_OFFSET_X, cls.DOT_OFFSET_Y) + start_point
        painter.drawEllipse(dot_point, cls.DOT_RADIUS, cls.DOT_RADIUS)
