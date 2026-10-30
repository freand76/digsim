# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""Components drawn as a body with their name and port names, like ICs"""

from __future__ import annotations

import math

from PySide6.QtCore import QPoint, QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QAction, QPainter, QPolygonF
from PySide6.QtWidgets import QMenu, QWidget

from digsim.circuit.components.atoms import DigsimException

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


class _MemoryObject(NamedBoxObject):
    """A RAM or ROM, its contents in the hex editor (Edit Contents... in its menu)"""

    def add_context_menu_action(self, menu: QMenu, parent: QWidget | None) -> None:
        action = QAction("Edit Contents...", menu)
        menu.addAction(action)
        action.triggered.connect(lambda: self._edit_contents(parent))

    def _edit_contents(self, parent: QWidget | None) -> None:
        # Here, the GUI imports the component objects
        from digsim.app.gui._hex_editor import HexEditorDialog

        # Not modal, the circuit can be used while it is open. An editor of this memory
        # that is open already comes to the front.
        if parent is not None:
            for dialog in parent.findChildren(HexEditorDialog):
                if dialog.memory_name == self.component.name() and dialog.isVisible():
                    dialog.raise_()
                    dialog.activateWindow()
                    return
        try:
            dialog = HexEditorDialog(parent, self._app_model, self)
        except DigsimException as exc:
            self._app_model.sig_error.emit(f"Could not read the contents: {exc!s}")
            return
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dialog.show()


class RAMObject(_MemoryObject):
    """A RAM placed in the GUI"""

    ICON_TEXT = "RAM"


class ROMObject(_MemoryObject):
    """A ROM placed in the GUI"""

    ICON_TEXT = "ROM"


class ArithmeticObject(ComponentObject):
    """
    An arithmetic component: a body with its operator in the middle, like + for an
    adder, and the names of its ports
    """

    PORT_ARROWS = True
    BORDER_TO_PORT = 15
    # The operator, and its font size
    SYMBOL = ""
    _SYMBOL_SIZE = 16

    def update_ports(self) -> None:
        super().update_ports()
        # Room for the operator between the names of the inputs and the outputs
        inputs = [self._port_names[port] for port in self.component.inports()]
        outputs = [self._port_names[port] for port in self.component.outports()]
        names = [
            max((self.get_string_metrics(name)[0] for name in group), default=0)
            for group in (inputs, outputs)
        ]
        symbol, _ = self.get_string_metrics(self.SYMBOL, theme.font(self._SYMBOL_SIZE, bold=True))
        width = math.ceil((2 * self.inport_x_pos() + sum(names) + symbol + 12) / 10) * 10
        if self.width < width:
            self.width = width
            super().update_ports()

    def paint_component(self, painter: QPainter) -> None:
        self.paint_component_base(painter)
        theme.paint_text(painter, QRectF(self.rect()), self.SYMBOL, self._SYMBOL_SIZE, bold=True)

    @classmethod
    def paint_selectable_component(cls, painter: QPainter, size: QSize, name: str) -> None:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(size.width() / 2 - 20, 14, 40, 50)
        theme.paint_body(painter, rect)
        # A longer operator, like <=>, smaller
        theme.paint_text(painter, rect, cls.SYMBOL, 14 if len(cls.SYMBOL) <= 2 else 10, bold=True)
        port_arrows(
            painter, [QPointF(rect.left() - 1, rect.top() + y) for y in (14, 36)], inputs=True
        )
        port_arrows(painter, [QPointF(rect.right(), rect.center().y())], inputs=False)
        painter.restore()
        cls.paint_selectable_component_name(painter, QPoint(0, 0), size, name)


class AdderObject(ArithmeticObject):
    """An adder placed in the GUI"""

    SYMBOL = "+"


class SubtractorObject(ArithmeticObject):
    """A subtractor placed in the GUI"""

    SYMBOL = "\u2212"


class MultiplierObject(ArithmeticObject):
    """A multiplier placed in the GUI"""

    SYMBOL = "\u00d7"


class ComparatorObject(ArithmeticObject):
    """A comparator placed in the GUI"""

    SYMBOL = "<=>"


class NegatorObject(ArithmeticObject):
    """A negator placed in the GUI"""

    SYMBOL = "\u2212x"


class CounterObject(NamedBoxObject):
    """A counter placed in the GUI"""

    ICON_TEXT = "CNT"
