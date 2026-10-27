# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""A probe placed in the GUI"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from PySide6.QtCore import QPoint, QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPainter

from digsim.circuit.components import Probe
from digsim.circuit.components.atoms import Component

from . import _theme as theme
from ._component_object import ComponentObject
from ._symbol_objects import port_dots


if TYPE_CHECKING:
    from digsim.app.model import AppModel


class ProbeObject(ComponentObject):
    """
    A probe: a small meter, a white body with a dark screen that shows the value of the
    wire or bus at its input
    """

    SHOW_PORT_NAMES = False
    HEIGHT = 22
    # The screen inside the body
    SCREEN_MARGIN = 3
    _FONT_SIZE = 8

    def __init__(
        self, app_model: AppModel, component: Component, xpos: float, ypos: float
    ) -> None:
        super().__init__(app_model, component, xpos, ypos)
        self.update_size()

    @property
    def component(self) -> Probe:
        component = self._component
        assert isinstance(component, Probe)
        return component

    def update_size(self) -> None:
        # Wide enough for the widest value, so that it doesn't change size while it runs
        text_width, _ = self.get_string_metrics(
            self.component.widest_text(), theme.font(self._FONT_SIZE, bold=True)
        )
        self.width = math.ceil((text_width + 2 * self.SCREEN_MARGIN + 10) / 10) * 10
        self.height = self.HEIGHT
        self.update_ports()

    @classmethod
    def paint_meter(
        cls, painter: QPainter, rect: QRectF, text: str, color: QColor, selected: bool = False
    ) -> None:
        """The body, and the screen with the text"""
        theme.paint_body(painter, rect, selected)
        screen = rect.adjusted(
            cls.SCREEN_MARGIN, cls.SCREEN_MARGIN, -cls.SCREEN_MARGIN, -cls.SCREEN_MARGIN
        )
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(theme.SCREEN)
        painter.drawRoundedRect(screen, 2, 2)
        theme.paint_text(
            painter,
            screen.adjusted(0, 0, -3, 0),
            text,
            cls._FONT_SIZE,
            color,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            bold=True,
        )

    def paint_component(self, painter: QPainter) -> None:
        # Undefined and not driven in the colors of the wires
        value = str(self.component.I.value)
        color = {"X": theme.WIRE_X, "Z": theme.WIRE_Z}.get(value, theme.READOUT)
        self.paint_meter(painter, QRectF(self.rect()), self.component.text(), color, self.selected)

    @classmethod
    def paint_selectable_component(cls, painter: QPainter, size: QSize, name: str) -> None:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        width = 40
        # Centered like the symbols of the other components
        rect = QRectF(
            size.width() / 2 - width / 2,
            size.width() / 2 - 2 - cls.HEIGHT / 2,
            width,
            cls.HEIGHT,
        )
        cls.paint_meter(painter, rect, "2A", theme.READOUT)
        port_dots(painter, [QPointF(rect.left(), rect.center().y())])
        painter.restore()
        cls.paint_selectable_component_name(painter, QPoint(0, 0), size, name)
