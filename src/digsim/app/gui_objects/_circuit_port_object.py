# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""The circuit ports (In, Out, InOut) placed in the GUI"""

from __future__ import annotations

import math
from functools import partial
from typing import TYPE_CHECKING

from PySide6.QtCore import QPoint, QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QAction, QPainter
from PySide6.QtWidgets import QInputDialog, QMenu, QWidget

from digsim.app._value_text import parse_value, value_text
from digsim.circuit.components import CircuitInOut, CircuitInput, CircuitOutput, CircuitPort
from digsim.circuit.components.atoms import Component

from . import _theme as theme
from ._component_object import ComponentObject
from ._named_box_object import port_arrows


if TYPE_CHECKING:
    from digsim.app.model import AppModel


class CircuitPortObject(ComponentObject):
    """
    A circuit port: a body with the name of the port and its value, and the port on the
    side it connects to the circuit: an In on the right, an Out on the left, an InOut on
    the right as a diamond
    """

    SHOW_PORT_NAMES = False
    PORT_ARROWS = True
    HEIGHT = 20
    _FONT_SIZE = 8

    def __init__(
        self, app_model: AppModel, component: Component, xpos: float, ypos: float
    ) -> None:
        super().__init__(app_model, component, xpos, ypos)
        self.update_size()

    @property
    def component(self) -> CircuitPort:
        component = self._component
        assert isinstance(component, CircuitPort)
        return component

    def _texts(self) -> tuple[str, str]:
        """The name, and the value"""
        port = self.component
        return port.label(), value_text(port.value, port.width)

    def update_size(self) -> None:
        # Wide enough for the name and the widest value
        name_width, _ = self.get_string_metrics(
            self.component.label(), theme.font(self._FONT_SIZE, bold=True)
        )
        widest = "X" if self.component.width == 1 else "F" * ((self.component.width + 3) // 4)
        value_width, _ = self.get_string_metrics(widest, theme.font(self._FONT_SIZE))
        self.width = math.ceil((name_width + value_width + 26) / 10) * 10
        self.height = self.HEIGHT
        self.update_ports()

    def paint_component(self, painter: QPainter) -> None:
        self.paint_component_base(painter)
        # Room for the arrow of an input on the left
        left = 10 if isinstance(self.component, CircuitOutput) else 6
        rect = QRectF(self.rect()).adjusted(left, 0, -6, 0)
        name, value = self._texts()
        theme.paint_text(
            painter,
            rect,
            name,
            self._FONT_SIZE,
            align=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            bold=True,
        )
        color = {"X": theme.WIRE_X, "Z": theme.WIRE_Z}.get(value, theme.INK)
        theme.paint_text(
            painter,
            rect,
            value,
            self._FONT_SIZE,
            color,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )

    def single_click_action(self) -> None:
        port = self.component
        if isinstance(port, CircuitInput) and port.width == 1:
            port.onpress()
            # While the simulation is stopped, the circuit settles with the new value
            self._app_model.model_settle()
            self.repaint()

    def add_context_menu_action(self, menu: QMenu, parent: QWidget | None) -> None:
        if isinstance(self.component, (CircuitInput, CircuitInOut)):
            action = QAction("Set Value...", menu)
            menu.addAction(action)
            action.triggered.connect(partial(self.ask_value, parent))

    def ask_value(self, parent: QWidget | None) -> None:
        """Set Value...: the value of an In, or what an InOut drives (or Z)"""
        port = self.component
        if isinstance(port, CircuitInOut):
            current = port.drive
            hint = "hexadecimal 0x.., binary 0b.., decimal, or Z (not driven)"
        elif isinstance(port, CircuitInput):
            current = port.value
            hint = "hexadecimal 0x.., binary 0b.. or decimal"
        else:
            return
        text, ok = QInputDialog.getText(
            parent,
            "Set Value",
            f"The value of {port.label()} ({port.width} bits), {hint}:",
            text=f"0x{current:X}" if isinstance(current, int) else str(current),
        )
        if not ok:
            return
        try:
            value = parse_value(text, port.width, allow_z=isinstance(port, CircuitInOut))
        except ValueError as exc:
            self._app_model.sig_error.emit(f"Could not set the value: {exc!s}")
            return
        set_value = partial(port.set_value, value) if isinstance(port, CircuitInOut) else None
        if isinstance(port, CircuitInput) and isinstance(value, int):
            set_value = partial(port.set_value, value)
        if set_value is None:
            return
        if self._app_model.is_running:
            # The simulation thread sets it
            self._app_model.model_add_event(set_value)
            return
        set_value()
        self._app_model.model_settle()
        self.repaint()

    # The text in the icon, and the side of its port
    ICON_TEXT = ""
    ICON_PORT_RIGHT = True

    @classmethod
    def paint_selectable_component(cls, painter: QPainter, size: QSize, name: str) -> None:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(size.width() / 2 - 24, size.width() / 2 - 2 - cls.HEIGHT / 2, 48, cls.HEIGHT)
        theme.paint_body(painter, rect)
        theme.paint_text(painter, rect, cls.ICON_TEXT, 7, bold=True)
        if cls.ICON_PORT_RIGHT:
            port_arrows(painter, [QPointF(rect.right(), rect.center().y())], inputs=False)
        else:
            port_arrows(painter, [QPointF(rect.left() - 1, rect.center().y())], inputs=True)
        painter.restore()
        cls.paint_selectable_component_name(painter, QPoint(0, 0), size, name)


class CircuitInputObject(CircuitPortObject):
    """An In of the circuit placed in the GUI"""

    ICON_TEXT = "in"


class CircuitOutputObject(CircuitPortObject):
    """An Out of the circuit placed in the GUI"""

    ICON_TEXT = "out"
    ICON_PORT_RIGHT = False


class CircuitInOutObject(CircuitPortObject):
    """An InOut of the circuit placed in the GUI"""

    ICON_TEXT = "io"
