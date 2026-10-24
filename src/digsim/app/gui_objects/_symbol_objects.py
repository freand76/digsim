# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""
Components drawn as a symbol only, without a body: gates, the tristate buffer, the
multiplexer, the LED and the bus splitters
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QPainter, QPainterPath

from digsim.circuit.components import Led
from digsim.circuit.components.atoms import Component, Port

from . import _theme as theme
from ._component_object import ComponentObject


if TYPE_CHECKING:
    from digsim.app.model import AppModel


def paint_icon(
    painter: QPainter,
    size: QSize,
    symbol_size: tuple[float, float],
    paint: Callable[[QRectF], None],
    scale: float = 1.0,
) -> None:
    """Paint a symbol as an icon of the component selector, centered above its name"""
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    width, height = symbol_size
    painter.translate(size.width() / 2, size.width() / 2 - 2)
    painter.scale(scale, scale)
    paint(QRectF(-width / 2, -height / 2, width, height))
    painter.restore()


def port_dots(painter: QPainter, points: list[QPointF]) -> None:
    """The ports of an icon, like the dots of the ports in the circuit"""
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(theme.INK)
    for point in points:
        painter.drawEllipse(point, 2.5, 2.5)


class SymbolObject(ComponentObject):
    """A component drawn as a symbol, the ports at the ends of its leads"""

    SHOW_PORT_NAMES = False

    def port_ys(self, ports: list[Port]) -> list[float]:
        """The y of each port, in the scene"""
        return [self.get_port_item(port).rect().center().y() for port in ports]


# Gates

LEAD = 8
BUBBLE = 3.0
# The body of a gate is as high as with two inputs. With more inputs the back of the
# gate is extended with a line, so that every gate has the same shape.
MAX_BODY = 36


def _body_rect(rect: QRectF, invert: bool, center_y: float) -> QRectF:
    right = rect.right() - LEAD - (2 * BUBBLE if invert else 0)
    height = min(rect.height() - 4, MAX_BODY)
    return QRectF(rect.left() + LEAD, center_y - height / 2, right - rect.left() - LEAD, height)


def _or_back_x(body: QRectF, depth: float, y: float) -> float:
    """The x of the curved back of an OR gate at y (a quadratic curve)"""
    half = body.height() / 2
    u = max(-1.0, min(1.0, (y - body.center().y()) / half))
    return body.left() + depth * (1 - u * u)


def gate_path(shape: str, body: QRectF) -> QPainterPath:
    """The outline of a gate: "and", "or" or "buffer" (a triangle)"""
    path = QPainterPath()
    left, top, right, bottom = body.left(), body.top(), body.right(), body.bottom()
    mid = body.center().y()
    if shape == "and":
        radius = min(body.height() / 2, body.width())
        path.moveTo(left, top)
        path.lineTo(right - radius, top)
        path.arcTo(QRectF(right - 2 * radius, top, 2 * radius, body.height()), 90, -180)
        path.lineTo(left, bottom)
        path.closeSubpath()
    elif shape == "or":
        depth = body.width() * 0.22
        path.moveTo(left, top)
        path.quadTo(left + body.width() * 0.6, top, right, mid)
        path.quadTo(left + body.width() * 0.6, bottom, left, bottom)
        path.quadTo(left + 2 * depth, mid, left, top)
    else:
        path.moveTo(left, top)
        path.lineTo(right, mid)
        path.lineTo(left, bottom)
        path.closeSubpath()
    return path


def paint_gate(
    painter: QPainter,
    rect: QRectF,
    shape: str,
    invert: bool,
    exclusive: bool,
    input_ys: list[float],
    output_y: float,
    selected: bool = False,
) -> None:
    """A gate in its rect, with a lead from each input and to the output"""
    body = _body_rect(rect, invert, output_y)
    if exclusive:
        # Room for the second curve of the XOR
        back = QRectF(body)
        body.setLeft(body.left() + 5)
    depth = body.width() * 0.22 if shape in ("or",) else 0.0
    # The back, where the inputs end, and the line that extends it
    back_x = back.left() if exclusive else body.left()
    for y in input_ys:
        if not body.top() < y < body.bottom():
            end = back_x
        elif exclusive:
            end = _or_back_x(back, back.width() * 0.22, y)
        elif shape == "or":
            end = _or_back_x(body, depth, y)
        else:
            end = body.left()
        theme.lead(painter, QPointF(rect.left() - 1, y), QPointF(end, y))
    output_x = body.right() + (2 * BUBBLE if invert else 0)
    theme.lead(painter, QPointF(output_x, output_y), QPointF(rect.right(), output_y))
    theme.symbol_path(painter, gate_path(shape, body), selected)
    top, bottom = min(input_ys), max(input_ys)
    if top < body.top() or bottom > body.bottom():
        painter.setPen(theme.outline_pen(selected))
        painter.drawLine(QPointF(back_x, top - 1), QPointF(back_x, body.top()))
        painter.drawLine(QPointF(back_x, body.bottom()), QPointF(back_x, bottom + 1))
    if exclusive:
        curve = QPainterPath()
        curve.moveTo(back.left(), back.top())
        curve.quadTo(
            back.left() + 2 * back.width() * 0.22, back.center().y(), back.left(), back.bottom()
        )
        painter.setPen(theme.outline_pen(selected))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(curve)
    if invert:
        theme.bubble(painter, QPointF(body.right() + BUBBLE, output_y), BUBBLE, selected)


class GateObject(SymbolObject):
    """A gate with 2 to 8 inputs, drawn as its symbol"""

    SHAPE = "and"
    INVERT = False
    EXCLUSIVE = False
    WIDTH = 50
    DENSE_INPUTS = 3
    DENSE_DISTANCE = 10

    def __init__(
        self, app_model: AppModel, component: Component, xpos: float, ypos: float
    ) -> None:
        super().__init__(app_model, component, xpos, ypos)
        self.update_size()

    def update_size(self) -> None:
        inputs = len(self.component.inports())
        self.width = self.WIDTH
        # The ports 10 pixels from the top and 20 apart, like the other components, or 10
        # apart when there are many, so that the gate is not too high
        self._port_distance = (
            self.DENSE_DISTANCE
            if inputs >= self.DENSE_INPUTS
            else self.DEFAULT_PORT_TO_PORT_DISTANCE
        )
        self.height = (inputs - 1) * self._port_distance + 2 * self.BORDER_TO_PORT
        self.update_ports()

    def paint_component(self, painter: QPainter) -> None:
        (output,) = self.component.outports()
        paint_gate(
            painter,
            QRectF(self.rect()),
            self.SHAPE,
            self.INVERT,
            self.EXCLUSIVE,
            self.port_ys(self.component.inports()),
            self.port_ys([output])[0],
            self.selected,
        )

    @classmethod
    def paint_selectable_component(cls, painter: QPainter, size: QSize, name: str) -> None:
        def paint(rect: QRectF) -> None:
            inputs = [rect.top() + 10, rect.bottom() - 10] if cls.SHAPE != "buffer" else []
            if not inputs:
                inputs = [rect.center().y()]
            paint_gate(
                painter, rect, cls.SHAPE, cls.INVERT, cls.EXCLUSIVE, inputs, rect.center().y()
            )
            port_dots(
                painter,
                [QPointF(rect.left() - 1, y) for y in inputs]
                + [QPointF(rect.right(), rect.center().y())],
            )

        height = 20 if cls.SHAPE == "buffer" else 40
        paint_icon(painter, size, (cls.WIDTH, height), paint, scale=1.15)
        cls.paint_selectable_component_name(painter, QPointF(0, 0), size, name)


class AndObject(GateObject):
    """An AND gate in the GUI"""


class NandObject(GateObject):
    """A NAND gate in the GUI"""

    INVERT = True


class OrObject(GateObject):
    """An OR gate in the GUI"""

    SHAPE = "or"


class NorObject(GateObject):
    """A NOR gate in the GUI"""

    SHAPE = "or"
    INVERT = True


class XorObject(GateObject):
    """An XOR gate in the GUI"""

    SHAPE = "or"
    EXCLUSIVE = True


class XnorObject(GateObject):
    """An XNOR gate in the GUI"""

    SHAPE = "or"
    EXCLUSIVE = True
    INVERT = True


class NotObject(GateObject):
    """A NOT gate in the GUI"""

    SHAPE = "buffer"
    INVERT = True
    WIDTH = 44


class TristateObject(SymbolObject):
    """
    A tristate buffer: A to Y through a triangle, the enable (OE) comes into it from below.
    Y is at the height of A.
    """

    WIDTH = 40

    def __init__(
        self, app_model: AppModel, component: Component, xpos: float, ypos: float
    ) -> None:
        super().__init__(app_model, component, xpos, ypos)
        self.width = self.WIDTH
        self.height = 40
        self.update_ports()

    def update_ports(self) -> None:
        super().update_ports()
        # Y at the height of A, not in the middle
        if hasattr(self, "_component"):
            a_rect = self.get_port_item(self.component.port("A")).rect()
            y_item = self.get_port_item(self.component.port("Y"))
            y_rect = y_item.rect()
            y_rect.moveTop(a_rect.top())
            y_item.setRect(y_rect)

    @staticmethod
    def paint_buffer(
        painter: QPainter, rect: QRectF, a_y: float, oe_y: float, bus: bool, selected: bool
    ) -> None:
        """The triangle from A to Y, and the enable from below"""
        # A short triangle, in the middle
        body = QRectF(rect.center().x() - 8, a_y - 9, 16, 18)
        width = 3.0 if bus else theme.LINE_WIDTH
        theme.lead(painter, QPointF(rect.left() - 1, a_y), QPointF(body.left(), a_y), width)
        theme.lead(painter, QPointF(body.right(), a_y), QPointF(rect.right(), a_y), width)
        enable_x = body.left() + body.width() * 0.45
        # The lower edge of the triangle at enable_x
        edge_y = body.bottom() - (enable_x - body.left()) / body.width() * body.height() / 2
        painter.setPen(theme.ink_pen())
        painter.setBrush(Qt.BrushStyle.NoBrush)
        enable = QPainterPath(QPointF(rect.left() - 1, oe_y))
        enable.lineTo(enable_x, oe_y)
        enable.lineTo(enable_x, edge_y)
        painter.drawPath(enable)
        theme.symbol_path(painter, gate_path("buffer", body), selected)

    def paint_component(self, painter: QPainter) -> None:
        (a_y,) = self.port_ys([self.component.port("A")])
        (oe_y,) = self.port_ys([self.component.port("OE")])
        bus = self.component.port("A").width > 1
        self.paint_buffer(painter, QRectF(self.rect()), a_y, oe_y, bus, self.selected)

    @classmethod
    def paint_selectable_component(cls, painter: QPainter, size: QSize, name: str) -> None:
        def paint(rect: QRectF) -> None:
            a_y, oe_y = rect.top() + 10, rect.bottom() - 10
            cls.paint_buffer(painter, rect, a_y, oe_y, False, False)
            port_dots(
                painter,
                [
                    QPointF(rect.left() - 1, a_y),
                    QPointF(rect.left() - 1, oe_y),
                    QPointF(rect.right(), a_y),
                ],
            )

        paint_icon(painter, size, (cls.WIDTH, 40), paint, scale=1.15)
        cls.paint_selectable_component_name(painter, QPointF(0, 0), size, name)


class MuxObject(SymbolObject):
    """A multiplexer, a trapezoid with the inputs to the left, S below them"""

    SHOW_PORT_NAMES = True
    WIDTH = 50

    def __init__(
        self, app_model: AppModel, component: Component, xpos: float, ypos: float
    ) -> None:
        super().__init__(app_model, component, xpos, ypos)
        self.width = self.WIDTH
        self.update_ports()

    @staticmethod
    def paint_mux(painter: QPainter, rect: QRectF, selected: bool) -> None:
        """The trapezoid"""
        inset = min(12.0, rect.height() / 4)
        path = QPainterPath(QPointF(rect.left() + 1, rect.top()))
        path.lineTo(rect.right() - 1, rect.top() + inset)
        path.lineTo(rect.right() - 1, rect.bottom() - inset)
        path.lineTo(rect.left() + 1, rect.bottom())
        path.closeSubpath()
        theme.symbol_path(painter, path, selected)

    def paint_component(self, painter: QPainter) -> None:
        self.paint_mux(painter, QRectF(self.rect()), self.selected)

    @classmethod
    def paint_selectable_component(cls, painter: QPainter, size: QSize, name: str) -> None:
        def paint(rect: QRectF) -> None:
            cls.paint_mux(painter, rect, False)
            ys = [rect.top() + 10, rect.top() + 30, rect.top() + 50]
            port_dots(
                painter,
                [QPointF(rect.left() + 1, y) for y in ys]
                + [QPointF(rect.right() - 1, rect.center().y())],
            )
            for text, y in zip(["A", "B", "S"], ys, strict=True):
                theme.paint_text(
                    painter,
                    QRectF(rect.left() + 5, y - 6, 12, 12),
                    text,
                    7,
                    align=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                )

        paint_icon(painter, size, (cls.WIDTH - 10, 60), paint, scale=1.0)
        cls.paint_selectable_component_name(painter, QPointF(0, 0), size, name)


class LedObject(SymbolObject):
    """
    An LED standing, seen from the side, in the color of the component. Its long leg
    bends to the input, below it.
    """

    WIDTH = 26
    HEIGHT = 40
    # From the top to the input
    PORT_Y = 30
    # The glow of a lit LED
    PAINT_MARGIN = 14

    def __init__(
        self, app_model: AppModel, component: Component, xpos: float, ypos: float
    ) -> None:
        super().__init__(app_model, component, xpos, ypos)
        self.width = self.WIDTH
        self.height = self.HEIGHT
        self.update_ports()

    @property
    def component(self) -> Led:
        component = self._component
        assert isinstance(component, Led)
        return component

    def update_ports(self) -> None:
        super().update_ports()
        # The input below the middle, where the leg of the LED bends to it
        item = self.get_port_item(self.component.I)
        port_rect = item.rect()
        port_rect.moveTop(self.rect().top() + self.PORT_Y - self.PORT_SIDE / 2)
        item.setRect(port_rect)

    @classmethod
    def paint_led(
        cls, painter: QPainter, rect: QRectF, color: str, lit: bool, selected: bool
    ) -> None:
        """The LED and its legs"""
        center_x = rect.left() + 16
        base = theme.paint_led(
            painter, center_x, rect.top() + 2, theme.led_color(color), lit, selected
        )
        port_y = rect.top() + cls.PORT_Y
        painter.setPen(theme.ink_pen())
        painter.setBrush(Qt.BrushStyle.NoBrush)
        # The long leg (anode) to the input, the short one (cathode) to ground
        anode = QPainterPath(QPointF(center_x - 2.5, base))
        anode.lineTo(center_x - 2.5, port_y)
        anode.lineTo(rect.left() - 1, port_y)
        painter.drawPath(anode)
        ground_x, ground_y = center_x + 2.5, port_y + 2
        painter.drawLine(QPointF(ground_x, base), QPointF(ground_x, ground_y))
        painter.setPen(theme.ink_pen(1.2))
        for step, half_width in enumerate((4.0, 2.5, 1.0)):
            y = ground_y + 2.5 * step
            painter.drawLine(QPointF(ground_x - half_width, y), QPointF(ground_x + half_width, y))

    def paint_component(self, painter: QPainter) -> None:
        self.paint_led(
            painter,
            QRectF(self.rect()),
            self.component.color,
            self.component.active,
            self.selected,
        )

    @classmethod
    def paint_selectable_component(cls, painter: QPainter, size: QSize, name: str) -> None:
        def paint(rect: QRectF) -> None:
            cls.paint_led(painter, rect, "red", True, False)
            port_dots(painter, [QPointF(rect.left() - 1, rect.top() + cls.PORT_Y)])

        paint_icon(painter, size, (cls.WIDTH, cls.HEIGHT), paint, scale=1.4)
        cls.paint_selectable_component_name(painter, QPointF(0, 0), size, name)


class BusBitsObject(SymbolObject):
    """
    A bus split into its bits (Bus2Wires): the bus comes into a thick bar, and each bit
    leaves it through a short slanted entry, numbered. The bus is marked with its width.
    """

    PORT_DISTANCE = 10
    # As wide as a device, the ports stay on the 10 pixel rhythm
    WIDTH = 40
    # From the bus side to the bar
    BAR = 14
    # The bits are to the right of the bar
    BITS_RIGHT = True

    def __init__(
        self, app_model: AppModel, component: Component, xpos: float, ypos: float
    ) -> None:
        super().__init__(app_model, component, xpos, ypos, port_distance=self.PORT_DISTANCE)
        self.width = self.WIDTH
        self.update_ports()

    def _bus_and_bits(self) -> tuple[Port, list[Port]]:
        if self.BITS_RIGHT:
            return self.component.inports()[0], self.component.outports()
        return self.component.outports()[0], self.component.inports()

    @classmethod
    def paint_bus_bits(
        cls,
        painter: QPainter,
        rect: QRectF,
        bus_y: float,
        bit_ys: list[float],
        selected: bool,
    ) -> None:
        """The bar, the bus to it and the bits from it"""
        mirror = 1 if cls.BITS_RIGHT else -1
        bar_x = rect.left() + cls.BAR if cls.BITS_RIGHT else rect.right() - cls.BAR
        entry = 4.0
        bus_end = rect.left() - 1 if cls.BITS_RIGHT else rect.right()
        bit_end = rect.right() if cls.BITS_RIGHT else rect.left() - 1
        color = theme.ACCENT if selected else theme.INK
        # The bus, with a slash and its width
        painter.setPen(theme.ink_pen(3.5, color))
        painter.drawLine(QPointF(bus_end, bus_y), QPointF(bar_x, bus_y))
        slash_x = (bus_end + bar_x) / 2
        painter.setPen(theme.ink_pen(1.2, color))
        painter.drawLine(QPointF(slash_x - 3, bus_y + 4), QPointF(slash_x + 3, bus_y - 4))
        theme.paint_text(
            painter,
            QRectF(slash_x - 8, bus_y - 15, 16, 9),
            str(len(bit_ys)),
            6,
            theme.MUTED,
        )
        # The bar
        painter.setPen(theme.ink_pen(4.0, color))
        painter.drawLine(QPointF(bar_x, bit_ys[0] - entry), QPointF(bar_x, bit_ys[-1] + entry))
        # The bits
        for bit, y in enumerate(bit_ys):
            path = QPainterPath(QPointF(bar_x, y + entry))
            path.lineTo(bar_x + mirror * entry, y)
            path.lineTo(bit_end, y)
            painter.setPen(theme.ink_pen(theme.LINE_WIDTH, color))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path)
            text_rect = (
                QRectF(bit_end - 18, y - 9, 12, 8)
                if cls.BITS_RIGHT
                else QRectF(bit_end + 6, y - 9, 12, 8)
            )
            theme.paint_text(
                painter,
                text_rect,
                str(bit),
                6,
                theme.MUTED,
                Qt.AlignmentFlag.AlignRight if cls.BITS_RIGHT else Qt.AlignmentFlag.AlignLeft,
            )

    def paint_component(self, painter: QPainter) -> None:
        bus, bits = self._bus_and_bits()
        self.paint_bus_bits(
            painter,
            QRectF(self.rect()),
            self.port_ys([bus])[0],
            self.port_ys(bits),
            self.selected,
        )

    @classmethod
    def paint_selectable_component(cls, painter: QPainter, size: QSize, name: str) -> None:
        def paint(rect: QRectF) -> None:
            bit_ys = [rect.top() + 5 + 10 * bit for bit in range(4)]
            bus_y = rect.center().y()
            cls.paint_bus_bits(painter, rect, bus_y, bit_ys, False)
            bus_x = rect.left() - 1 if cls.BITS_RIGHT else rect.right()
            bit_x = rect.right() if cls.BITS_RIGHT else rect.left() - 1
            port_dots(painter, [QPointF(bus_x, bus_y)] + [QPointF(bit_x, y) for y in bit_ys])

        paint_icon(painter, size, (cls.WIDTH, 40), paint, scale=1.15)
        cls.paint_selectable_component_name(painter, QPointF(0, 0), size, name)


class BitsBusObject(BusBitsObject):
    """Wires joined into a bus (Wires2Bus), the bus splitter mirrored"""

    BITS_RIGHT = False
