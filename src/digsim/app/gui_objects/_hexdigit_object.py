# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""A hexdigit component placed in the GUI"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QPointF, QSize
from PySide6.QtGui import QPainter

from digsim.circuit.components import HexDigit
from digsim.circuit.components.atoms import Component

from ._seven_segment_object import SevenSegmentObject


if TYPE_CHECKING:
    from digsim.app.model import AppModel


class HexDigitObject(SevenSegmentObject):
    """The class for a hexdigit component placed in the GUI"""

    def __init__(
        self, app_model: AppModel, component: Component, xpos: float, ypos: float
    ) -> None:
        super().__init__(
            app_model,
            component,
            xpos,
            ypos,
            port_distance=10,
        )

    @property
    def component(self) -> HexDigit:
        component = self._component
        assert isinstance(component, HexDigit)
        return component

    def setup_size(self) -> None:
        """Setup the size of the component"""
        self.digits = self.component.get_digits()
        str_pixels_w, _ = self.get_string_metrics(f"val[{4 * self.digits - 1}:0]")
        self.digit_left = self.inport_x_pos() + str_pixels_w + self.PORT_TO_RECT_MARGIN
        self.digit_top = self.RECT_TO_DIGIT_RECT_MARGIN
        self.width = (
            self.digit_left
            + self.digits * self.DIGIT_WIDTH * self.SCALE
            + self.RECT_TO_DIGIT_RECT_MARGIN
        )
        self.height = 2 * self.RECT_TO_DIGIT_RECT_MARGIN + self.DIGIT_HEIGHT * self.SCALE
        self.update_ports()

    def paint_component(self, painter: QPainter) -> None:
        self.paint_component_base(painter)
        self.paint_digits(
            painter,
            QPointF(self.object_pos.x() + self.digit_left, self.object_pos.y() + self.digit_top),
            [self.component.segments(digit_id) for digit_id in range(self.digits)],
        )

    @classmethod
    def paint_selectable_component(cls, painter: QPainter, size: QSize, name: str) -> None:
        cls.paint_selectable_digit(painter, size, name, "ABDEG")
