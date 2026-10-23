# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""A GUI note object"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, QSize
from PySide6.QtGui import QFontMetrics, QPainter, QPainterPath

from digsim.circuit.components.atoms import Component

from . import _theme as theme
from ._component_object import ComponentObject


if TYPE_CHECKING:
    from digsim.app.model import AppModel


class GuiNoteObject(ComponentObject):
    """The class for a note placed in the GUI"""

    NOTE_BORDER = 10
    NOTE_MINIMUM_WIDTH = 50
    NOTE_MINIMUM_HEIGHT = 20

    _NOTE_FONT = theme.font(8)

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
        self._paint_note(painter, QRectF(self.rect()), self.selected)
        painter.setPen(theme.INK)
        painter.setFont(self._NOTE_FONT)
        for idx, line in enumerate(lines):
            painter.drawText(
                int(self.object_pos.x() + self.NOTE_BORDER),
                int(self.object_pos.y() + self.NOTE_BORDER + (idx + 1) * fm.height()),
                line,
            )

    @staticmethod
    def _paint_note(painter: QPainter, rect: QRectF, selected: bool) -> None:
        """A note with a folded corner"""
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        fold = 8.0
        path = QPainterPath(rect.topLeft())
        path.lineTo(rect.right() - fold, rect.top())
        path.lineTo(rect.right(), rect.top() + fold)
        path.lineTo(rect.bottomRight())
        path.lineTo(rect.bottomLeft())
        path.closeSubpath()
        if selected:
            painter.setPen(theme.outline_pen(True))
        else:
            painter.setPen(theme.ink_pen(1.0, theme.dim(theme.NOTE, 0.75, theme.INK)))
        painter.setBrush(theme.NOTE)
        painter.drawPath(path)
        corner = QPainterPath(QPointF(rect.right() - fold, rect.top()))
        corner.lineTo(rect.right() - fold, rect.top() + fold)
        corner.lineTo(rect.right(), rect.top() + fold)
        painter.setPen(theme.ink_pen(1.0, theme.dim(theme.NOTE, 0.75, theme.INK)))
        painter.setBrush(theme.dim(theme.NOTE, 0.85, theme.INK))
        painter.drawPath(corner)

    @classmethod
    def paint_selectable_component(cls, painter: QPainter, size: QSize, name: str) -> None:
        note_rect = QRect(
            cls.NOTE_BORDER,
            cls.NOTE_BORDER,
            size.width() - 2 * cls.NOTE_BORDER,
            size.width() - 2 * cls.NOTE_BORDER,
        )
        cls._paint_note(painter, QRectF(note_rect), False)
        painter.setPen(theme.INK)
        painter.setFont(cls._NOTE_FONT)
        fm = QFontMetrics(cls._NOTE_FONT)
        painter.drawText(2 * cls.NOTE_BORDER, 2 * cls.NOTE_BORDER + fm.height(), "abc..")
        cls.paint_selectable_component_name(painter, QPoint(0, 0), size, name)
