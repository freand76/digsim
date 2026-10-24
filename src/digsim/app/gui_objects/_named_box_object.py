# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""Components drawn as a body with their name and port names, like ICs"""

from __future__ import annotations

from PySide6.QtCore import QPoint, QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QPainter

from . import _theme as theme
from ._component_object import ComponentObject


class NamedBoxObject(ComponentObject):
    """
    A base class for components drawn as a body with their name and port names, like an
    IC. The name is in a header above the ports.
    """

    BORDER_TO_PORT = 25

    def paint_component(self, painter: QPainter) -> None:
        self.paint_component_base(painter)
        self.paint_component_name(painter)
        # The header
        painter.setPen(theme.ink_pen(1.0, theme.OFF))
        y = self.rect().top() + 16
        painter.drawLine(QPointF(self.rect().left() + 4, y), QPointF(self.rect().right() - 4, y))

    @classmethod
    def paint_selectable_component(cls, painter: QPainter, size: QSize, name: str) -> None:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(size.width() / 2 - 22, 10, 44, 58)
        theme.paint_body(painter, rect)
        painter.setPen(theme.ink_pen(1.0, theme.OFF))
        painter.drawLine(
            QPointF(rect.left() + 4, rect.top() + 14), QPointF(rect.right() - 4, rect.top() + 14)
        )
        theme.paint_text(
            painter,
            QRectF(rect.left(), rect.top() + 1, rect.width(), 13),
            cls.ICON_TEXT,
            7,
            bold=True,
        )
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(theme.INK)
        for row in range(3):
            y = rect.top() + 24 + 12 * row
            painter.drawEllipse(QPointF(rect.left() - 1, y), 2.5, 2.5)
            if row < 2:
                painter.drawEllipse(QPointF(rect.right(), y), 2.5, 2.5)
        painter.restore()
        cls.paint_selectable_component_name(painter, QPoint(0, 0), size, name)

    # The text in the header of the icon
    ICON_TEXT = ""


class ICObject(NamedBoxObject):
    """An IC placed in the GUI"""

    ICON_TEXT = "74xx"
