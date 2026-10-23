# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""
The look of the components: one set of colors, lines and fonts, and the drawing of the
parts that several components have, like a body, an LED or a switch.

Components that are a symbol, like a gate, an LED or a bus splitter, are drawn as the
symbol only. Components that are a device, like a switch or a display, have a white body.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPainterPath, QPen, QRadialGradient


# Lines and text
INK = QColor("#33414e")
# Text and lines that are less important, like bit numbers
MUTED = QColor("#7d8a96")
BODY = QColor("#ffffff")
# A selected component
ACCENT = QColor("#2d7ff9")
# The window of a display, like a 7-segment digit
DISPLAY = QColor("#1f2429")
BACKGROUND = QColor("#e6e9ec")
GRID = QColor("#c8ced5")
NOTE = QColor("#fff4b8")
# Wires: 0 (or not colored), undefined (X), not driven (Z). 1 is ON, a bus between
WIRE = QColor("#8c96a0")
WIRE_X = QColor("#e5484d")
WIRE_Z = QColor("#3e7bfa")
# Switches that are on, and wires that are 1
ON = QColor("#27a55a")
OFF = QColor("#c3cad1")

LINE_WIDTH = 1.5
SYMBOL_WIDTH = 2.0
CORNER = 4

# The colors of LEDs, lit
LED_COLORS = {
    "red": QColor("#ff3b30"),
    "green": QColor("#34d058"),
    "blue": QColor("#2f8cff"),
    "yellow": QColor("#ffd60a"),
}

FONT_FAMILY = "Arial"


def font(size: int = 8, bold: bool = False) -> QFont:
    """The font of the components, in a size"""
    qfont = QFont(FONT_FAMILY, size)
    qfont.setBold(bold)
    return qfont


def ink_pen(width: float = LINE_WIDTH, color: QColor | None = None) -> QPen:
    """A pen for lines, with round joins"""
    pen = QPen(INK if color is None else color, width)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    return pen


def outline_pen(selected: bool) -> QPen:
    """The pen of a body or a symbol, in the accent color when it is selected"""
    if selected:
        return ink_pen(2.5, ACCENT)
    return ink_pen()


def paint_body(
    painter: QPainter, rect: QRectF, selected: bool = False, fill: QColor = BODY
) -> None:
    """The white body of a device"""
    painter.setPen(outline_pen(selected))
    painter.setBrush(fill)
    painter.drawRoundedRect(rect, CORNER, CORNER)


def paint_window(painter: QPainter, rect: QRectF) -> None:
    """The dark window of a display"""
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(DISPLAY)
    painter.drawRoundedRect(rect, 2, 2)


def led_color(name: str) -> QColor:
    """The color of a lit LED, red if the name is not an LED color"""
    return LED_COLORS.get(name, LED_COLORS["red"])


def dim(color: QColor, factor: float = 0.3, toward: QColor | None = None) -> QColor:
    """A color mixed with another (dark gray by default), like an LED that is off"""
    base = QColor("#3a3f44") if toward is None else toward
    return QColor(
        int(base.red() + (color.red() - base.red()) * factor),
        int(base.green() + (color.green() - base.green()) * factor),
        int(base.blue() + (color.blue() - base.blue()) * factor),
    )


def paint_led(painter: QPainter, center: QPointF, radius: float, color: QColor, lit: bool) -> None:
    """
    A round LED seen from above: a rim, a lens with a highlight, and a glow around it
    when it is lit
    """
    if lit:
        glow = QRadialGradient(center, radius * 1.9)
        glow_color = QColor(color)
        glow_color.setAlpha(110)
        glow.setColorAt(0.45, glow_color)
        glow_color.setAlpha(0)
        glow.setColorAt(1.0, glow_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(glow))
        painter.drawEllipse(center, radius * 1.9, radius * 1.9)
    # The rim
    painter.setPen(ink_pen(1.0))
    painter.setBrush(dim(color, 0.55, INK) if lit else dim(color, 0.35))
    painter.drawEllipse(center, radius, radius)
    # The lens
    lens = QRadialGradient(center - QPointF(radius * 0.3, radius * 0.3), radius)
    if lit:
        lens.setColorAt(0.0, dim(color, 0.25, QColor("#ffffff")))
        lens.setColorAt(0.6, color)
        lens.setColorAt(1.0, dim(color, 0.8, INK))
    else:
        lens.setColorAt(0.0, dim(color, 0.6))
        lens.setColorAt(1.0, dim(color, 0.25))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(lens))
    painter.drawEllipse(center, radius * 0.78, radius * 0.78)
    # The highlight
    shine = QColor(255, 255, 255, 170 if lit else 90)
    painter.setBrush(shine)
    painter.drawEllipse(center - QPointF(radius * 0.3, radius * 0.32), radius * 0.2, radius * 0.14)


def paint_bar_led(painter: QPainter, rect: QRectF, color: QColor, lit: bool) -> None:
    """A rectangular LED, of an LED bar"""
    if lit:
        glow = QColor(color)
        glow.setAlpha(90)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(glow)
        painter.drawRoundedRect(rect.adjusted(-2, -2, 2, 2), 3, 3)
        painter.setBrush(color)
    else:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(dim(color, 0.3))
    painter.drawRoundedRect(rect, 1.5, 1.5)


def paint_toggle(painter: QPainter, rect: QRectF, on: bool, highlight: bool = False) -> None:
    """A slide switch: a track with a knob to the right when it is on"""
    radius = rect.height() / 2
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(ON if on else OFF)
    painter.drawRoundedRect(rect, radius, radius)
    knob = radius - 1.5
    x = rect.right() - radius if on else rect.left() + radius
    painter.setPen(ink_pen(1.0, ACCENT if highlight else dim(INK, 0.6, OFF)))
    painter.setBrush(BODY)
    painter.drawEllipse(QPointF(x, rect.center().y()), knob, knob)


def paint_text(
    painter: QPainter,
    rect: QRectF,
    text: str,
    size: int = 8,
    color: QColor = INK,
    align: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignCenter,
    bold: bool = False,
) -> None:
    """Text in a rect"""
    painter.setPen(color)
    painter.setFont(font(size, bold))
    painter.drawText(rect, int(align), text)


def lead(painter: QPainter, start: QPointF, end: QPointF, width: float = LINE_WIDTH) -> None:
    """A line from a port to a symbol"""
    painter.setPen(ink_pen(width))
    painter.drawLine(start, end)


def bubble(painter: QPainter, center: QPointF, radius: float, selected: bool) -> None:
    """The circle of an inverted output"""
    painter.setPen(outline_pen(selected))
    painter.setBrush(BODY)
    painter.drawEllipse(center, radius, radius)


def symbol_path(painter: QPainter, path: QPainterPath, selected: bool) -> None:
    """A symbol, like a gate, filled white"""
    painter.setPen(outline_pen(selected))
    painter.setBrush(BODY)
    painter.drawPath(path)
