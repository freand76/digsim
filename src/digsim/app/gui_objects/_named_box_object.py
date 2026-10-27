# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""Components drawn as a body with their name and port names, like ICs"""

from __future__ import annotations

import math

from PySide6.QtCore import QPoint, QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QPainter, QPolygonF

from . import _theme as theme
from ._component_object import ComponentObject


def port_arrows(painter: QPainter, points: list[QPointF], inputs: bool) -> None:
    """
    The ports of an icon, like the arrows of the ports in the circuit: inputs on the left
    side, pointing into the body and mostly inside it, or outputs on the right side,
    pointing out of it
    """
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(theme.INK)
    for point in points:
        # 4/5 of an input is inside the body, half of an output
        tip = point.x() + (6.4 if inputs else 4)
        painter.drawPolygon(
            QPolygonF(
                [
                    QPointF(tip, point.y()),
                    QPointF(tip - 8, point.y() - 4),
                    QPointF(tip - 8, point.y() + 4),
                ]
            )
        )


class NamedBoxObject(ComponentObject):
    """
    A base class for components drawn as a body with their name and port names, like an
    IC. The name is in a header above the ports.
    """

    BORDER_TO_PORT = 25
    PORT_ARROWS = True

    def update_ports(self) -> None:
        # Wide enough for the name, in steps of 10 so that the outputs stay on the rhythm
        # of the ports, and high enough for one port below the header
        name_width, _ = self.get_string_metrics(
            self._component.display_name(), self._COMPONENT_NAME_FONT
        )
        self.width = max(self.width, math.ceil((name_width + 12) / 10) * 10)
        self.height = max(self.height, 2 * self.BORDER_TO_PORT)
        super().update_ports()

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
        ys = [rect.top() + 24 + 12 * row for row in range(3)]
        port_arrows(painter, [QPointF(rect.left() - 1, y) for y in ys], inputs=True)
        port_arrows(painter, [QPointF(rect.right(), y) for y in ys[:2]], inputs=False)
        painter.restore()
        cls.paint_selectable_component_name(painter, QPoint(0, 0), size, name)

    # The text in the header of the icon
    ICON_TEXT = ""


class ICObject(NamedBoxObject):
    """An IC placed in the GUI"""

    ICON_TEXT = "74xx"


class RAMObject(NamedBoxObject):
    """A RAM placed in the GUI"""

    ICON_TEXT = "RAM"


class ROMObject(NamedBoxObject):
    """A ROM placed in the GUI"""

    ICON_TEXT = "ROM"
