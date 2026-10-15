# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""A GUI note object"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtGui import QFont, QFontMetrics, QPainter, QPen

from digsim.circuit.components.atoms import Component

from ._component_object import ComponentObject


if TYPE_CHECKING:
    from digsim.app.model import AppModel


class GuiNoteObject(ComponentObject):
    """The class for a note placed in the GUI"""

    NOTE_BORDER = 10
    NOTE_MINIMUM_WIDTH = 50
    NOTE_MINIMUM_HEIGHT = 20

    _NOTE_FONT = QFont("Arial", 8)
    _NOTE_PEN = QPen(Qt.GlobalColor.black)

    def __init__(
        self, app_model: AppModel, component: Component, xpos: float, ypos: float
    ) -> None:
        super().__init__(app_model, component, xpos, ypos)
        self.update_size()

    def _get_lines(self) -> list[str]:
        return self.component.parameter_get("text").split("\n")

    def update_size(self) -> None:
        fm = QFontMetrics(self._NOTE_FONT)
        width = self.NOTE_MINIMUM_WIDTH
        lines = self._get_lines()
        for line in lines:
            str_pixels_w = fm.horizontalAdvance(line)
            width = max(width, str_pixels_w)
        self.width = width + 2 * self.NOTE_BORDER
        self.height = max(
            self.NOTE_MINIMUM_HEIGHT,
            2 * self.NOTE_BORDER + len(lines) * fm.height(),
        )

    def paint_component(self, painter: QPainter) -> None:
        """Paint note rectangle"""
        fm = QFontMetrics(self._NOTE_FONT)
        lines = self._get_lines()
        # A copy: the class pen is shared by all instances
        pen = QPen(self._NOTE_PEN)
        if self.selected:
            pen.setWidth(4)
        else:
            pen.setWidth(1)
        painter.setPen(pen)
        painter.setBrush(Qt.GlobalColor.yellow)
        painter.drawRect(self.rect())
        painter.setFont(self._NOTE_FONT)
        for idx, line in enumerate(lines):
            painter.drawText(
                int(self.object_pos.x() + self.NOTE_BORDER),
                int(self.object_pos.y() + self.NOTE_BORDER + (idx + 1) * fm.height()),
                line,
            )

    @classmethod
    def paint_selectable_component(cls, painter: QPainter, size: QSize, name: str) -> None:
        note_rect = QRect(
            cls.NOTE_BORDER,
            cls.NOTE_BORDER,
            size.width() - 2 * cls.NOTE_BORDER,
            size.width() - 2 * cls.NOTE_BORDER,
        )
        # A copy: the class pen is shared by all instances
        pen = QPen(cls._NOTE_PEN)
        pen.setWidth(1)
        painter.setPen(pen)
        painter.setBrush(Qt.GlobalColor.yellow)
        painter.drawRect(note_rect)
        painter.setFont(cls._NOTE_FONT)
        fm = QFontMetrics(cls._NOTE_FONT)
        painter.drawText(2 * cls.NOTE_BORDER, 2 * cls.NOTE_BORDER + fm.height(), "abc..")
        cls.paint_selectable_component_name(painter, QPoint(0, 0), size, name)
