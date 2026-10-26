# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""A label component placed in the GUI"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, QSize
from PySide6.QtGui import QPainter, QPolygon

from digsim.circuit.components import LabelWireIn, LabelWireOut
from digsim.circuit.components.atoms import Component

from . import _theme as theme
from ._component_object import ComponentObject
from ._symbol_objects import port_dots


if TYPE_CHECKING:
    from digsim.app.model import AppModel


class LabelObject(ComponentObject):
    """The base class for the label wire components (Wire Sink and Wire Source) in the GUI"""

    # A Wire Sink, which takes the signal in (LabelWireIn), or a Wire Source
    SINK: bool
    # The label is the name of the port, drawn in the tag
    SHOW_PORT_NAMES = False

    def __init__(
        self, app_model: AppModel, component: Component, xpos: float, ypos: float
    ) -> None:
        super().__init__(app_model, component, xpos, ypos)
        label = self.component.label()
        label_w, _ = self.get_string_metrics(label, theme.font(7))
        self.width = 2 * self.PORT_SIDE + label_w + 4
        self.height = 20

        if self.SINK:
            xpos = -ComponentObject.RECT_TO_BORDER
        else:
            # At the tip, like the outputs of other components
            xpos = ComponentObject.RECT_TO_BORDER + self.width - self.PORT_SIDE - 1
        rect = QRect(
            int(self.object_pos.x() + xpos),
            int(self.object_pos.y() + self.height / 2 - self.PORT_SIDE / 2),
            self.PORT_SIDE,
            self.PORT_SIDE,
        )
        port = self.component.port(label)
        self.set_port_rect(port, rect)

    @property
    def component(self) -> LabelWireIn | LabelWireOut:
        component = self._component
        assert isinstance(component, (LabelWireIn, LabelWireOut))
        return component

    @classmethod
    def _paint_label(
        cls, painter: QPainter, comp_rect: QRect | QRectF, selected: bool = False
    ) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(theme.outline_pen(selected))
        painter.setBrush(theme.BODY)

        if cls.SINK:
            points = QPolygon(
                [
                    QPoint(int(comp_rect.x()), int(comp_rect.y() + comp_rect.height() / 2)),
                    QPoint(int(comp_rect.x() + comp_rect.height() / 2), int(comp_rect.y())),
                    QPoint(int(comp_rect.x() + comp_rect.width()), int(comp_rect.y())),
                    QPoint(
                        int(comp_rect.x() + comp_rect.width()),
                        int(comp_rect.y() + comp_rect.height()),
                    ),
                    QPoint(
                        int(comp_rect.x() + comp_rect.height() / 2),
                        int(comp_rect.y() + comp_rect.height()),
                    ),
                    QPoint(int(comp_rect.x()), int(comp_rect.y() + comp_rect.height() / 2)),
                ]
            )
        else:
            points = QPolygon(
                [
                    QPoint(int(comp_rect.x()), int(comp_rect.y())),
                    QPoint(
                        int(comp_rect.x() + comp_rect.width() - comp_rect.height() / 2),
                        int(comp_rect.y()),
                    ),
                    QPoint(
                        int(comp_rect.x() + comp_rect.width()),
                        int(comp_rect.y() + comp_rect.height() / 2),
                    ),
                    QPoint(
                        int(comp_rect.x() + comp_rect.width() - comp_rect.height() / 2),
                        int(comp_rect.y() + comp_rect.height()),
                    ),
                    QPoint(int(comp_rect.x()), int(comp_rect.y() + comp_rect.height())),
                    QPoint(int(comp_rect.x()), int(comp_rect.y())),
                ]
            )
        painter.drawPolygon(points)

    def paint_component(self, painter: QPainter) -> None:
        self._paint_label(painter, self.rect(), self.selected)
        rect = QRectF(self.rect())
        text = (
            rect.adjusted(rect.height() / 2, 0, -2, 0)
            if self.SINK
            else rect.adjusted(2, 0, -rect.height() / 2, 0)
        )
        theme.paint_text(painter, text, self.component.label(), 7)

    @classmethod
    def paint_selectable_component(cls, painter: QPainter, size: QSize, name: str) -> None:
        width = 44
        height = 16
        # Centered like the symbols of the other components
        rect = QRectF(
            size.width() / 2 - width / 2, size.width() / 2 - 2 - height / 2, width, height
        )
        cls._paint_label(painter, rect)
        theme.paint_text(painter, rect, "label", 7)
        # The port, at the tip
        tip_x = rect.left() if cls.SINK else rect.right()
        port_dots(painter, [QPointF(tip_x, rect.center().y())])
        cls.paint_selectable_component_name(painter, QPoint(0, 0), size, name)


class LabelWireInObject(LabelObject):
    """The class for a Wire Sink (LabelWireIn) placed in the GUI"""

    SINK = True


class LabelWireOutObject(LabelObject):
    """The class for a Wire Source (LabelWireOut) placed in the GUI"""

    SINK = False
