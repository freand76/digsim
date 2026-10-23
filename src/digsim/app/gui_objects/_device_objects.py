# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""
Components drawn as a device, a white body with a symbol or text: the push button, the
switch, the clock, the static value and the flip-flops
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QAction, QColor, QPainter, QPainterPath
from PySide6.QtWidgets import QMenu, QWidget

from digsim.circuit.components import OnOffSwitch
from digsim.circuit.components.atoms import Component

from . import _theme as theme
from ._component_object import ComponentObject
from ._shortcut_objects import ShortcutMenu
from ._symbol_objects import paint_icon, port_dots


if TYPE_CHECKING:
    from digsim.app.model import AppModel


class DeviceObject(ComponentObject):
    """A small device: a white body with a symbol in it, painted by paint_face()"""

    SHOW_PORT_NAMES = False
    SIZE = (40.0, 40.0)
    # A light in the corner, green while the component is active
    STATUS_LIGHT = False

    def __init__(
        self, app_model: AppModel, component: Component, xpos: float, ypos: float
    ) -> None:
        super().__init__(app_model, component, xpos, ypos)
        self.width, self.height = self.SIZE
        self.update_ports()

    @classmethod
    def paint_face(cls, painter: QPainter, rect: QRectF, active: bool) -> None:
        """The symbol in the body, of a component that is active or not"""

    @classmethod
    def paint_status_light(cls, painter: QPainter, rect: QRectF, active: bool) -> None:
        """The light in the top right corner"""
        if cls.STATUS_LIGHT:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(theme.ON if active else theme.OFF)
            painter.drawEllipse(QPointF(rect.right() - 6, rect.top() + 6), 2.5, 2.5)

    def paint_component(self, painter: QPainter) -> None:
        self.paint_component_base(painter)
        self.paint_face(painter, QRectF(self.rect()), self.component.active)
        self.paint_status_light(painter, QRectF(self.rect()), self.component.active)

    @classmethod
    def paint_selectable_component(cls, painter: QPainter, size: QSize, name: str) -> None:
        def paint(rect: QRectF) -> None:
            theme.paint_body(painter, rect)
            cls.paint_face(painter, rect, False)
            cls.paint_status_light(painter, rect, False)
            port_dots(painter, [QPointF(rect.right(), rect.center().y())])

        paint_icon(painter, size, cls.SIZE, paint, scale=1.3)
        cls.paint_selectable_component_name(painter, QPointF(0, 0), size, name)


def _contacts(painter: QPainter, center: QPointF) -> tuple[QPointF, QPointF]:
    """The two contacts of a switch symbol, with a lead from each to the side"""
    left = QPointF(center.x() - 9, center.y() + 6)
    right = QPointF(center.x() + 9, center.y() + 6)
    painter.setPen(theme.ink_pen())
    painter.drawLine(QPointF(center.x() - 15, left.y()), QPointF(left.x() - 2, left.y()))
    painter.drawLine(QPointF(right.x() + 2, right.y()), QPointF(center.x() + 15, right.y()))
    painter.setBrush(theme.BODY)
    painter.drawEllipse(left, 2, 2)
    painter.drawEllipse(right, 2, 2)
    return left, right


class ButtonObject(DeviceObject):
    """
    A push button, as the symbol of a push switch: a bridge on a plunger over two
    contacts. Pushed, the bridge is down on the contacts, in green.
    """

    STATUS_LIGHT = True

    @classmethod
    def paint_face(cls, painter: QPainter, rect: QRectF, active: bool) -> None:
        left, right = _contacts(painter, rect.center())
        bridge_y = left.y() - 2 if active else left.y() - 8
        color = theme.ON if active else theme.INK
        painter.setPen(theme.ink_pen(theme.SYMBOL_WIDTH, color))
        painter.drawLine(QPointF(left.x() - 2, bridge_y), QPointF(right.x() + 2, bridge_y))
        # The plunger, with its handle
        top = bridge_y - 9
        painter.drawLine(QPointF(rect.center().x(), bridge_y), QPointF(rect.center().x(), top))
        painter.drawLine(QPointF(rect.center().x() - 5, top), QPointF(rect.center().x() + 5, top))

    def add_context_menu_action(self, menu: QMenu, parent: QWidget | None) -> None:
        ShortcutMenu.add_context_menu_action(menu, parent, self._app_model, self._component)


class OnOffSwitchObject(DeviceObject):
    """An on/off switch, as the symbol of a switch, its lever closed and green when on"""

    STATUS_LIGHT = True

    @property
    def component(self) -> OnOffSwitch:
        component = self._component
        assert isinstance(component, OnOffSwitch)
        return component

    @classmethod
    def paint_face(cls, painter: QPainter, rect: QRectF, active: bool) -> None:
        """The symbol of a switch: a lever from one contact, on the other when it is on"""
        left, right = _contacts(painter, rect.center())
        end = (
            QPointF(right.x() + 1, right.y() - 2) if active else QPointF(right.x(), right.y() - 12)
        )
        painter.setPen(theme.ink_pen(theme.SYMBOL_WIDTH, theme.ON if active else theme.INK))
        painter.drawLine(left, end)

    def single_click_action(self) -> None:
        self._toggle()

    def add_context_menu_action(self, menu: QMenu, parent: QWidget | None) -> None:
        ShortcutMenu.add_context_menu_action(menu, parent, self._app_model, self._component)
        toggleAction = QAction("Toggle Switch", menu)
        menu.addAction(toggleAction)
        toggleAction.triggered.connect(self._toggle)

    def _toggle(self) -> None:
        self.component.toggle()
        self.repaint()


class ClockObject(DeviceObject):
    """A clock: a square wave, green while the output is 1"""

    STATUS_LIGHT = True

    @classmethod
    def paint_face(cls, painter: QPainter, rect: QRectF, active: bool) -> None:
        center = rect.center()
        low, high = center.y() + 6, center.y() - 6
        path = QPainterPath(QPointF(center.x() - 13, low))
        for x0, x1 in ((-13, -6), (-6, 1), (1, 8)):
            y = low if x0 in (-13, 1) else high
            path.lineTo(center.x() + x0, y)
            path.lineTo(center.x() + x1, y)
            path.lineTo(center.x() + x1, high if y == low else low)
        path.lineTo(center.x() + 13, path.currentPosition().y())
        painter.setPen(theme.ink_pen(theme.SYMBOL_WIDTH, theme.ON if active else theme.INK))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)


class StaticValueObject(DeviceObject):
    """A constant: its value, as wide as it needs"""

    SIZE = (30.0, 20.0)

    def __init__(
        self, app_model: AppModel, component: Component, xpos: float, ypos: float
    ) -> None:
        super().__init__(app_model, component, xpos, ypos)
        text_width, _ = self.get_string_metrics(self._text(), theme.font(11, bold=True))
        self.width = max(self.SIZE[0], text_width + 16)
        self.update_ports()

    def _text(self) -> str:
        return str(self.component.parameter_get("value"))

    def paint_component(self, painter: QPainter) -> None:
        self.paint_component_base(painter)
        theme.paint_text(painter, QRectF(self.rect()), self._text(), 11, bold=True)

    @classmethod
    def paint_face(cls, painter: QPainter, rect: QRectF, active: bool) -> None:
        theme.paint_text(painter, rect, "1", 11, bold=True)


class FlipFlopObject(ComponentObject):
    """
    A flip-flop: a body with its port names, and the clock input (C) marked with a
    triangle
    """

    CLOCK_PORTS = ("C", "clk", "Clk", "CLK", "clock")

    def __init__(
        self, app_model: AppModel, component: Component, xpos: float, ypos: float
    ) -> None:
        super().__init__(app_model, component, xpos, ypos)
        self.width = 50
        self.update_ports()

    def paint_component(self, painter: QPainter) -> None:
        self.paint_component_base(painter)
        for port in self.component.inports():
            if port.name() in self.CLOCK_PORTS:
                y = self.get_port_item(port).rect().center().y()
                x = self.rect().left()
                path = QPainterPath(QPointF(x, y - 4))
                path.lineTo(x + 6, y)
                path.lineTo(x, y + 4)
                painter.setPen(theme.ink_pen(1.2))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawPath(path)

    def paint_portnames(
        self, painter: QPainter, color: QColor | Qt.GlobalColor = theme.INK
    ) -> None:
        """The port names, the clock's after its triangle"""
        painter.setPen(color)
        painter.setFont(self._PORT_NAME_FONT)
        for port in self.component.ports:
            rect = self.get_port_item(port).rect()
            text = QRectF(self.rect().left() + 4, rect.center().y() - 6, self.width - 8, 12)
            if port.is_output():
                align = Qt.AlignmentFlag.AlignRight
            else:
                align = Qt.AlignmentFlag.AlignLeft
                if port.name() in self.CLOCK_PORTS:
                    continue
            painter.drawText(
                text, int(align | Qt.AlignmentFlag.AlignVCenter), self._port_names[port]
            )

    @classmethod
    def paint_selectable_component(cls, painter: QPainter, size: QSize, name: str) -> None:
        def paint(rect: QRectF) -> None:
            theme.paint_body(painter, rect)
            mid = rect.center().y()
            for text, y, align in (
                ("D", mid - 10, Qt.AlignmentFlag.AlignLeft),
                ("Q", mid, Qt.AlignmentFlag.AlignRight),
            ):
                theme.paint_text(
                    painter,
                    QRectF(rect.left() + 4, y - 6, rect.width() - 8, 12),
                    text,
                    7,
                    align=align | Qt.AlignmentFlag.AlignVCenter,
                )
            path = QPainterPath(QPointF(rect.left(), mid + 6))
            path.lineTo(rect.left() + 6, mid + 10)
            path.lineTo(rect.left(), mid + 14)
            painter.setPen(theme.ink_pen(1.2))
            painter.drawPath(path)
            port_dots(
                painter,
                [
                    QPointF(rect.left() - 1, mid - 10),
                    QPointF(rect.left() - 1, mid + 10),
                    QPointF(rect.right(), mid),
                ],
            )

        paint_icon(painter, size, (50, 40), paint, scale=1.2)
        cls.paint_selectable_component_name(painter, QPointF(0, 0), size, name)
