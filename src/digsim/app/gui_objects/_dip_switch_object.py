# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""A DIP switch component placed in the GUI"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QPainter

from digsim.circuit.components import DipSwitch
from digsim.circuit.components.atoms import Component

from . import _theme as theme
from ._component_object import ComponentObject
from ._symbol_objects import paint_icon, port_dots


if TYPE_CHECKING:
    from digsim.app.model import AppModel


class DipSwitchObject(ComponentObject):
    """A DIP switch: a slide switch for each output, numbered from 1 like on the part"""

    SHOW_PORT_NAMES = False
    SWITCH_WIDTH = 18
    SWITCH_HEIGHT = 8
    SWITCH_DISTANCE = 10

    def __init__(
        self, app_model: AppModel, component: Component, xpos: float, ypos: float
    ) -> None:
        super().__init__(app_model, component, xpos, ypos, port_distance=self.SWITCH_DISTANCE)
        self.width = 40
        self.height = (self.component.bits() - 1) * self.SWITCH_DISTANCE + 2 * self.BORDER_TO_PORT
        self._rects: list[QRectF] = []
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
            y = self.get_port_pos(f"{idx}").y()
            self._rects.append(self.switch_rect(QRectF(self.rect()), y))

    @classmethod
    def switch_rect(cls, rect: QRectF, y: float) -> QRectF:
        """The switch in a row of the DIP switch"""
        return QRectF(
            rect.right() - 6 - cls.SWITCH_WIDTH,
            y - cls.SWITCH_HEIGHT / 2,
            cls.SWITCH_WIDTH,
            cls.SWITCH_HEIGHT,
        )

    def mouse_position(self, pos: QPointF) -> None:
        """update component according to on mouse move"""
        select = None
        pos = pos - self.pos()
        for idx, rect in enumerate(self._rects):
            if rect.contains(pos):
                select = idx
                break
        # Repaint only when another switch is highlighted, not on every mouse move
        if select != self.component.selected():
            self.component.select(select)
            self.repaint()

    def single_click_action(self) -> None:
        self.component.toggle()
        self.repaint()

    @classmethod
    def paint_switches(
        cls, painter: QPainter, rect: QRectF, ys: list[float], on: list[bool], selected: int | None
    ) -> None:
        """The switches and their numbers"""
        for idx, y in enumerate(ys):
            theme.paint_toggle(painter, cls.switch_rect(rect, y), on[idx], idx == selected)
            theme.paint_text(
                painter,
                QRectF(rect.left() + 2, y - 5, 10, 10),
                str(idx + 1),
                6,
                theme.MUTED,
                Qt.AlignmentFlag.AlignCenter,
            )

    def paint_component(self, painter: QPainter) -> None:
        self.paint_component_base(painter)
        bits = range(self.component.bits())
        self.paint_switches(
            painter,
            QRectF(self.rect()),
            [self.get_port_pos(f"{idx}").y() for idx in bits],
            [self.component.is_set(idx) for idx in bits],
            self.component.selected(),
        )

    @classmethod
    def paint_selectable_component(cls, painter: QPainter, size: QSize, name: str) -> None:
        def paint(rect: QRectF) -> None:
            theme.paint_body(painter, rect)
            ys = [rect.top() + 10 + 10 * idx for idx in range(4)]
            cls.paint_switches(painter, rect, ys, [True, False, True, True], None)
            port_dots(painter, [QPointF(rect.right(), y) for y in ys])

        paint_icon(painter, size, (40, 50), paint, scale=1.3)
        cls.paint_selectable_component_name(painter, QPointF(0, 0), size, name)
