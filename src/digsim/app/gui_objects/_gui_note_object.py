# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""A GUI note object"""

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QFont, QFontMetrics, QPen

from ._component_object import ComponentObject


class GuiNoteObject(ComponentObject):
    """The class for a note placed in the GUI"""

    NOTE_BORDER = 10
    NOTE_MINIMUM_WIDTH = 50
    NOTE_MINIMUM_HEIGHT = 20

    _NOTE_FONT = QFont("Arial", 8)
    _NOTE_PEN = QPen(Qt.black)

    def __init__(self, app_model, component, xpos, ypos):
        super().__init__(app_model, component, xpos, ypos)
        self.update_size()

    def _get_lines(self):
        return self.component.parameter_get("text").split("\n")

    def update_size(self):
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

    def paint_component(self, painter):
        """Paint note rectangle"""
        fm = QFontMetrics(self._NOTE_FONT)
        lines = self._get_lines()
        pen = self._NOTE_PEN
        if self.selected:
            pen.setWidth(4)
        else:
            pen.setWidth(1)
        painter.setPen(pen)
        painter.setBrush(Qt.SolidPattern)
        painter.setBrush(Qt.yellow)
        painter.drawRect(self.rect())
        painter.setFont(self._NOTE_FONT)
        for idx, line in enumerate(lines):
            painter.drawText(
                self.object_pos.x() + self.NOTE_BORDER,
                self.object_pos.y() + self.NOTE_BORDER + (idx + 1) * fm.height(),
                line,
            )

    @classmethod
    def paint_selectable_component(cls, painter, size, name):
        note_rect = QRect(
            cls.NOTE_BORDER,
            cls.NOTE_BORDER,
            size.width() - 2 * cls.NOTE_BORDER,
            size.width() - 2 * cls.NOTE_BORDER,
        )
        pen = cls._NOTE_PEN
        pen.setWidth(1)
        painter.setPen(pen)
        painter.setBrush(Qt.SolidPattern)
        painter.setBrush(Qt.yellow)
        painter.drawRect(note_rect)
        painter.setFont(cls._NOTE_FONT)
        fm = QFontMetrics(cls._NOTE_FONT)
        painter.drawText(2 * cls.NOTE_BORDER, 2 * cls.NOTE_BORDER + fm.height(), "abc..")
        cls.paint_selectable_component_name(painter, QPoint(0, 0), size, name)
