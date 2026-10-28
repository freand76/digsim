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

from digsim.circuit.components import Led, Splitter
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
# The length of the triangle of a buffer
TRIANGLE = 16
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
    if shape == "buffer":
        # The short triangle of the tristate buffer, in the middle
        body = QRectF(body.center().x() - TRIANGLE / 2, output_y - 9, TRIANGLE, 18)
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
    WIDTH = 40


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
        body = QRectF(rect.center().x() - TRIANGLE / 2, a_y - 9, TRIANGLE, 18)
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
    """
    A multiplexer, a trapezoid with the inputs to the left on leads like the gates, the
    names of the inputs inside, and S coming into it from below
    """

    WIDTH = 40
    # The inputs are 10 pixels apart from this many, like the gates
    DENSE_INPUTS = 4
    DENSE_DISTANCE = 10

    def __init__(
        self, app_model: AppModel, component: Component, xpos: float, ypos: float
    ) -> None:
        super().__init__(app_model, component, xpos, ypos)
        self.update_size()

    def update_size(self) -> None:
        # The inputs without S
        inputs = len(self.component.inports()) - 1
        self._port_distance = (
            self.DENSE_DISTANCE
            if inputs >= self.DENSE_INPUTS
            else self.DEFAULT_PORT_TO_PORT_DISTANCE
        )
        self.width = self.WIDTH
        # S is 20 pixels below the last input, room to come in from below
        self.height = (
            (inputs - 1) * self._port_distance
            + self.DEFAULT_PORT_TO_PORT_DISTANCE
            + 2 * self.BORDER_TO_PORT
        )
        self.update_ports()

    def update_ports(self) -> None:
        super().update_ports()
        if not hasattr(self, "_component"):
            return
        *inputs, select = self.component.inports()
        top = int(self.object_pos.y() + self.BORDER_TO_PORT - self.PORT_SIDE / 2)
        for idx, port in enumerate(inputs):
            self._move_port(port, top + idx * self._port_distance)
        last = top + (len(inputs) - 1) * self._port_distance
        self._move_port(select, last + self.DEFAULT_PORT_TO_PORT_DISTANCE)
        # Y in the middle of the inputs
        self._move_port(self.component.port("Y"), (top + last) // 2)

    def _move_port(self, port: Port, top: int) -> None:
        item = self.get_port_item(port)
        rect = item.rect()
        rect.moveTop(top)
        item.setRect(rect)

    @staticmethod
    def paint_mux(
        painter: QPainter,
        rect: QRectF,
        inputs: list[tuple[str, float, bool]],
        select: tuple[float, bool],
        output: tuple[float, bool],
        selected: bool,
    ) -> None:
        """
        The trapezoid and the leads, each input is (name, y, is a bus), and select and
        output are (y, is a bus)
        """
        ys = [y for _, y, _ in inputs]
        body = QRectF(rect.left() + LEAD, rect.top(), rect.width() - 2 * LEAD, 0)
        body.setBottom(ys[-1] + (ys[0] - rect.top()))
        output_y, output_bus = output
        for _, y, bus in inputs:
            width = 3.0 if bus else theme.LINE_WIDTH
            theme.lead(painter, QPointF(rect.left() - 1, y), QPointF(body.left(), y), width)
        width = 3.0 if output_bus else theme.LINE_WIDTH
        theme.lead(
            painter, QPointF(body.right(), output_y), QPointF(rect.right(), output_y), width
        )
        inset = min(10.0, body.height() / 4)
        # S from below, into the slanted lower edge
        select_y, select_bus = select
        select_x = body.center().x()
        edge_y = body.bottom() - inset / 2
        painter.setPen(theme.ink_pen(3.0 if select_bus else theme.LINE_WIDTH))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        path = QPainterPath(QPointF(rect.left() - 1, select_y))
        path.lineTo(select_x, select_y)
        path.lineTo(select_x, edge_y)
        painter.drawPath(path)
        trapezoid = QPainterPath(QPointF(body.left(), body.top()))
        trapezoid.lineTo(body.right(), body.top() + inset)
        trapezoid.lineTo(body.right(), body.bottom() - inset)
        trapezoid.lineTo(body.left(), body.bottom())
        trapezoid.closeSubpath()
        theme.symbol_path(painter, trapezoid, selected)
        for name, y, _ in inputs:
            theme.paint_text(
                painter,
                QRectF(body.left() + 3, y - 5, body.width() - 4, 10),
                name,
                6,
                align=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            )

    def paint_component(self, painter: QPainter) -> None:
        *inputs, select = self.component.inports()
        (output,) = self.component.outports()
        self.paint_mux(
            painter,
            QRectF(self.rect()),
            [(port.name(), self.port_ys([port])[0], port.width > 1) for port in inputs],
            (self.port_ys([select])[0], select.width > 1),
            (self.port_ys([output])[0], output.width > 1),
            self.selected,
        )

    @classmethod
    def paint_selectable_component(cls, painter: QPainter, size: QSize, name: str) -> None:
        def paint(rect: QRectF) -> None:
            ys = [rect.top() + 10, rect.top() + 30]
            select_y = rect.top() + 50
            output_y = rect.top() + 20
            inputs = [(text, y, False) for text, y in zip(["A", "B"], ys, strict=True)]
            cls.paint_mux(painter, rect, inputs, (select_y, False), (output_y, False), False)
            port_dots(
                painter,
                [QPointF(rect.left() - 1, y) for y in [*ys, select_y]]
                + [QPointF(rect.right(), output_y)],
            )

        paint_icon(painter, size, (cls.WIDTH, 60), paint, scale=1.0)
        cls.paint_selectable_component_name(painter, QPointF(0, 0), size, name)


class DemuxObject(SymbolObject):
    """
    A demultiplexer or a decoder: the trapezoid of a multiplexer mirrored, the outputs to
    the right with their names inside, the data input I (or the enable EN of a decoder)
    to the left, and S coming into it from below
    """

    WIDTH = 40
    # The outputs are 10 pixels apart from this many, like the inputs of a multiplexer
    DENSE_OUTPUTS = 4
    DENSE_DISTANCE = 10

    def __init__(
        self, app_model: AppModel, component: Component, xpos: float, ypos: float
    ) -> None:
        super().__init__(app_model, component, xpos, ypos)
        self.update_size()

    def _left_input(self) -> Port | None:
        """The input to the left: I of a demultiplexer, EN of a decoder (if it has it)"""
        names = [port.name() for port in self.component.inports()]
        for name in ("I", "EN"):
            if name in names:
                return self.component.port(name)
        return None

    def update_size(self) -> None:
        outputs = len(self.component.outports())
        self._port_distance = (
            self.DENSE_DISTANCE
            if outputs >= self.DENSE_OUTPUTS
            else self.DEFAULT_PORT_TO_PORT_DISTANCE
        )
        left = self._left_input()
        # Wider with the name EN inside, next to the names of the outputs
        self.width = self.WIDTH + (16 if left is not None and left.name() == "EN" else 0)
        # S is 20 pixels below the last output, room to come in from below
        self.height = (
            (outputs - 1) * self._port_distance
            + self.DEFAULT_PORT_TO_PORT_DISTANCE
            + 2 * self.BORDER_TO_PORT
        )
        self.update_ports()

    def update_ports(self) -> None:
        super().update_ports()
        if not hasattr(self, "_component"):
            return
        outputs = self.component.outports()
        top = int(self.object_pos.y() + self.BORDER_TO_PORT - self.PORT_SIDE / 2)
        for idx, port in enumerate(outputs):
            self._move_port(port, top + idx * self._port_distance)
        last = top + (len(outputs) - 1) * self._port_distance
        self._move_port(self.component.port("S"), last + self.DEFAULT_PORT_TO_PORT_DISTANCE)
        left = self._left_input()
        if left is not None:
            # In the middle of the outputs
            self._move_port(left, (top + last) // 2)

    def _move_port(self, port: Port, top: int) -> None:
        item = self.get_port_item(port)
        rect = item.rect()
        rect.moveTop(top)
        item.setRect(rect)

    @staticmethod
    def paint_demux(
        painter: QPainter,
        rect: QRectF,
        outputs: list[tuple[str, float, bool]],
        left: tuple[str, float, bool] | None,
        select: tuple[float, bool],
        selected: bool,
    ) -> None:
        """
        The trapezoid and the leads, each output (and the input to the left) is (name, y,
        is a bus), and select is (y, is a bus)
        """
        ys = [y for _, y, _ in outputs]
        body = QRectF(rect.left() + LEAD, rect.top(), rect.width() - 2 * LEAD, 0)
        body.setBottom(ys[-1] + (ys[0] - rect.top()))
        for _, y, bus in outputs:
            width = 3.0 if bus else theme.LINE_WIDTH
            theme.lead(painter, QPointF(body.right(), y), QPointF(rect.right(), y), width)
        if left is not None:
            _, left_y, left_bus = left
            theme.lead(
                painter,
                QPointF(rect.left() - 1, left_y),
                QPointF(body.left(), left_y),
                3.0 if left_bus else theme.LINE_WIDTH,
            )
        inset = min(10.0, body.height() / 4)
        # S from below, into the slanted lower edge
        select_y, select_bus = select
        select_x = body.center().x()
        edge_y = body.bottom() - inset / 2
        painter.setPen(theme.ink_pen(3.0 if select_bus else theme.LINE_WIDTH))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        path = QPainterPath(QPointF(rect.left() - 1, select_y))
        path.lineTo(select_x, select_y)
        path.lineTo(select_x, edge_y)
        painter.drawPath(path)
        trapezoid = QPainterPath(QPointF(body.left(), body.top() + inset))
        trapezoid.lineTo(body.right(), body.top())
        trapezoid.lineTo(body.right(), body.bottom())
        trapezoid.lineTo(body.left(), body.bottom() - inset)
        trapezoid.closeSubpath()
        theme.symbol_path(painter, trapezoid, selected)
        for name, y, _ in outputs:
            theme.paint_text(
                painter,
                QRectF(body.left() + 1, y - 5, body.width() - 4, 10),
                name,
                6,
                align=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            )
        if left is not None and left[0] == "EN":
            theme.paint_text(
                painter,
                QRectF(body.left() + 3, left[1] - 5, body.width() - 4, 10),
                "EN",
                6,
                align=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            )

    def paint_component(self, painter: QPainter) -> None:
        select = self.component.port("S")
        left = self._left_input()
        self.paint_demux(
            painter,
            QRectF(self.rect()),
            [
                (port.name(), self.port_ys([port])[0], port.width > 1)
                for port in self.component.outports()
            ],
            None if left is None else (left.name(), self.port_ys([left])[0], left.width > 1),
            (self.port_ys([select])[0], select.width > 1),
            self.selected,
        )

    # The input to the left of the icon: I of a demultiplexer, none on a decoder
    ICON_INPUT: str | None = "I"

    @classmethod
    def paint_selectable_component(cls, painter: QPainter, size: QSize, name: str) -> None:
        def paint(rect: QRectF) -> None:
            ys = [rect.top() + 10, rect.top() + 30]
            select_y = rect.top() + 50
            left_y = rect.top() + 20
            outputs = [(text, y, False) for text, y in zip(["Y0", "Y1"], ys, strict=True)]
            left = None if cls.ICON_INPUT is None else (cls.ICON_INPUT, left_y, False)
            cls.paint_demux(painter, rect, outputs, left, (select_y, False), False)
            port_dots(
                painter,
                [QPointF(rect.left() - 1, select_y)]
                + ([] if left is None else [QPointF(rect.left() - 1, left_y)])
                + [QPointF(rect.right(), y) for y in ys],
            )

        paint_icon(painter, size, (cls.WIDTH, 60), paint, scale=1.0)
        cls.paint_selectable_component_name(painter, QPointF(0, 0), size, name)


class DecoderObject(DemuxObject):
    """A decoder, drawn like a demultiplexer without a data input"""

    ICON_INPUT = None


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
            # Lower than the other icons, so that the glow fits above the LED
            rect = rect.translated(0, 6)
            cls.paint_led(painter, rect, "red", True, False)
            port_dots(painter, [QPointF(rect.left() - 1, rect.top() + cls.PORT_Y)])

        paint_icon(painter, size, (cls.WIDTH, cls.HEIGHT), paint, scale=1.25)
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

    def bits_right(self) -> bool:
        """True if the bits are to the right of the bar, the bus to the left"""
        return self.BITS_RIGHT

    def _bus_and_bits(self) -> tuple[Port, list[Port]]:
        if self.bits_right():
            return self.component.inports()[0], self.component.outports()
        return self.component.outports()[0], self.component.inports()

    def bit_labels(self, bits: list[Port]) -> list[str]:
        """The text next to each bit, its number (bus_5 is bit 5)"""
        return [bit.name().rpartition("_")[2] for bit in bits]

    @classmethod
    def paint_bus_bits(
        cls,
        painter: QPainter,
        rect: QRectF,
        bus_y: float,
        bit_ys: list[float],
        selected: bool,
        bits_right: bool,
        labels: list[str],
        bus_width: int,
        bit_widths: list[int] | None = None,
    ) -> None:
        """
        The bar, the bus to it and the bits from it, each with its label. Bits wider
        than one (the groups of a splitter) are drawn thicker.
        """
        mirror = 1 if bits_right else -1
        bar_x = rect.left() + cls.BAR if bits_right else rect.right() - cls.BAR
        entry = 4.0
        bus_end = rect.left() - 1 if bits_right else rect.right()
        bit_end = rect.right() if bits_right else rect.left() - 1
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
            str(bus_width),
            6,
            theme.MUTED,
        )
        # The bar
        painter.setPen(theme.ink_pen(4.0, color))
        painter.drawLine(QPointF(bar_x, bit_ys[0] - entry), QPointF(bar_x, bit_ys[-1] + entry))
        # The bits
        widths = bit_widths if bit_widths is not None else [1] * len(bit_ys)
        text_width = rect.width() - cls.BAR - 2 * entry - 2
        for label, y, width in zip(labels, bit_ys, widths):
            path = QPainterPath(QPointF(bar_x, y + entry))
            path.lineTo(bar_x + mirror * entry, y)
            path.lineTo(bit_end, y)
            pen_width = theme.LINE_WIDTH if width == 1 else 2.5
            painter.setPen(theme.ink_pen(pen_width, color))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path)
            text_rect = (
                QRectF(bit_end - 6 - text_width, y - 9, text_width, 8)
                if bits_right
                else QRectF(bit_end + 6, y - 9, text_width, 8)
            )
            theme.paint_text(
                painter,
                text_rect,
                label,
                6,
                theme.MUTED,
                Qt.AlignmentFlag.AlignRight if bits_right else Qt.AlignmentFlag.AlignLeft,
            )

    def paint_component(self, painter: QPainter) -> None:
        bus, bits = self._bus_and_bits()
        self.paint_bus_bits(
            painter,
            QRectF(self.rect()),
            self.port_ys([bus])[0],
            self.port_ys(bits),
            self.selected,
            self.bits_right(),
            self.bit_labels(bits),
            bus.width,
            [bit.width for bit in bits],
        )

    @classmethod
    def paint_bus_bits_icon(
        cls,
        painter: QPainter,
        size: QSize,
        name: str,
        labels: list[str],
        bus_width: int,
        bit_widths: list[int],
    ) -> None:
        """The icon: the bus and the bits, with the dots of their ports"""

        def paint(rect: QRectF) -> None:
            spacing = 10 if len(labels) > 3 else 14
            top = rect.center().y() - spacing * (len(labels) - 1) / 2
            bit_ys = [top + spacing * bit for bit in range(len(labels))]
            bus_y = rect.center().y()
            cls.paint_bus_bits(
                painter, rect, bus_y, bit_ys, False, cls.BITS_RIGHT, labels, bus_width, bit_widths
            )
            bus_x = rect.left() - 1 if cls.BITS_RIGHT else rect.right()
            bit_x = rect.right() if cls.BITS_RIGHT else rect.left() - 1
            port_dots(painter, [QPointF(bus_x, bus_y)] + [QPointF(bit_x, y) for y in bit_ys])

        paint_icon(painter, size, (cls.WIDTH, 40), paint, scale=1.15)
        cls.paint_selectable_component_name(painter, QPointF(0, 0), size, name)

    @classmethod
    def paint_selectable_component(cls, painter: QPainter, size: QSize, name: str) -> None:
        cls.paint_bus_bits_icon(painter, size, name, ["0", "1", "2", "3"], 4, [1, 1, 1, 1])


class BitsBusObject(BusBitsObject):
    """Wires joined into a bus (Wires2Bus), the bus splitter mirrored"""

    BITS_RIGHT = False


class SplitterObject(BusBitsObject):
    """
    A bus split into groups of bits (Splitter), or groups merged into a bus: drawn like
    Bus2Wires, with the bit range of each group and the groups wider than a bit thicker
    """

    # Room for the bit ranges, like 31:24
    WIDTH = 50
    PORT_DISTANCE = 20

    @property
    def component(self) -> Splitter:
        component = self._component
        assert isinstance(component, Splitter)
        return component

    def bits_right(self) -> bool:
        return not self.component.is_merge()

    def bit_labels(self, bits: list[Port]) -> list[str]:
        return [
            str(msb) if msb == lsb else f"{msb}:{lsb}"
            for msb, lsb in self.component.group_ranges()
        ]

    @classmethod
    def paint_selectable_component(cls, painter: QPainter, size: QSize, name: str) -> None:
        cls.paint_bus_bits_icon(painter, size, name, ["3:0", "4", "7:5"], 8, [4, 1, 3])
