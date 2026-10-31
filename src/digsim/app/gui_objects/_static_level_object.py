# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""GND and VDD in the GUI: the symbols of ground and of the supply, a constant 0 and 1"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QPointF, QRectF, QSize
from PySide6.QtGui import QPainter

from digsim.app._wire_route import rotated
from digsim.circuit.components.atoms import Component, Port

from . import _theme as theme
from ._symbol_objects import SymbolObject, paint_icon, port_dots


if TYPE_CHECKING:
    from digsim.app.model import AppModel


class _StaticLevelObject(SymbolObject):
    """
    A small symbol with its output in the middle of its top (GND) or its bottom (VDD), a
    wire leaves it up or down
    """

    # Like the symbols of a schematic, it stays upright
    ROTATABLE = False

    WIDTH = 20
    HEIGHT = 20
    # The output at the top, else at the bottom
    PORT_ON_TOP = True

    def __init__(
        self, app_model: AppModel, component: Component, xpos: float, ypos: float
    ) -> None:
        super().__init__(app_model, component, xpos, ypos)
        self.update_ports()

    def update_ports(self) -> None:
        self.width = self.WIDTH
        self.height = self.HEIGHT
        top_left = self.object_pos
        x = top_left.x() + self.WIDTH / 2
        # Like the pins of the LCD: half out of the rect
        if self.PORT_ON_TOP:
            y = top_left.y() - self.RECT_TO_BORDER
        else:
            y = top_left.y() + self.HEIGHT + self.RECT_TO_BORDER - self.PORT_SIDE
        for port in self._component.ports:
            self.set_port_rect(
                port, QRectF(x - self.PORT_SIDE / 2, y, self.PORT_SIDE, self.PORT_SIDE)
            )
        self._apply_rotation()

    def port_direction(self, port: Port) -> str:
        return rotated("up" if self.PORT_ON_TOP else "down", self._rotation)

    @classmethod
    def paint_symbol(cls, painter: QPainter, rect: QRectF, selected: bool) -> None:
        """The symbol in its rect"""

    def paint_component(self, painter: QPainter) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.paint_symbol(painter, QRectF(self.rect()), self.selected)

    @classmethod
    def paint_selectable_component(cls, painter: QPainter, size: QSize, name: str) -> None:
        def paint(rect: QRectF) -> None:
            cls.paint_symbol(painter, rect, False)
            y = rect.top() if cls.PORT_ON_TOP else rect.bottom()
            port_dots(painter, [QPointF(rect.center().x(), y)])

        paint_icon(painter, size, (cls.WIDTH, cls.HEIGHT), paint, scale=1.6)
        cls.paint_selectable_component_name(painter, QPointF(0, 0), size, name)


class GndObject(_StaticLevelObject):
    """GND: a lead down from its output to the three bars of ground, a constant 0"""

    PORT_ON_TOP = True

    @classmethod
    def paint_symbol(cls, painter: QPainter, rect: QRectF, selected: bool) -> None:
        x = rect.center().x()
        bars_y = rect.top() + 10
        theme.lead(painter, QPointF(x, rect.top()), QPointF(x, bars_y))
        painter.setPen(theme.outline_pen(selected))
        for step, half_width in enumerate((7.0, 4.5, 2.0)):
            y = bars_y + 4 * step
            painter.drawLine(QPointF(x - half_width, y), QPointF(x + half_width, y))


class VddObject(_StaticLevelObject):
    """VDD: the bar of the supply, and a lead down from it to its output, a constant 1"""

    PORT_ON_TOP = False

    @classmethod
    def paint_symbol(cls, painter: QPainter, rect: QRectF, selected: bool) -> None:
        x = rect.center().x()
        bar_y = rect.top() + 4
        theme.lead(painter, QPointF(x, bar_y), QPointF(x, rect.bottom()))
        painter.setPen(theme.ink_pen(2.5, theme.ACCENT) if selected else theme.ink_pen(2.0))
        painter.drawLine(QPointF(x - 7, bar_y), QPointF(x + 7, bar_y))
