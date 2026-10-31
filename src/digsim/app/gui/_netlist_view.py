# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""
A read-only view of the netlist of a Verilog component: its cells (gates drawn as their
symbols, other cells as blocks with their names) and the wires between them, laid out from
the inputs on the left to the outputs on the right. The ports show the values of the
simulation.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QFontMetricsF, QPainter, QPen
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QStyleOptionGraphicsItem,
    QWidget,
)

from digsim.app._line_graph import junctions
from digsim.app._netlist_layout import NodeShape, netlist_layout
from digsim.app.gui_objects import ComponentObject
from digsim.app.gui_objects import _theme as theme
from digsim.app.gui_objects._symbol_objects import paint_gate
from digsim.circuit import Circuit
from digsim.circuit.components import CircuitInOut, CircuitInput, CircuitOutput, YosysComponent
from digsim.circuit.components._yosys_component import NetlistParts
from digsim.utils import NetlistGraph, Pin, YosysCell, netlist_graph

from ._view_items import ViewInOut, ViewInput, ViewOutput


if TYPE_CHECKING:
    from digsim.app.model import AppModel

# The gate cells drawn as their symbols: (shape, inverted, exclusive), see paint_gate()
GATE_SYMBOLS = {
    "$_AND_": ("and", False, False),
    "$_NAND_": ("and", True, False),
    "$_OR_": ("or", False, False),
    "$_NOR_": ("or", True, False),
    "$_XOR_": ("or", False, True),
    "$_XNOR_": ("or", True, True),
    "$_BUF_": ("buffer", False, False),
    "$_NOT_": ("buffer", True, False),
}
GATE_WIDTH = 50.0
PORT_DISTANCE = 20.0
# The header of a block, with the name of its cell, and the space beside its port names
HEADER = 20.0
TEXT_MARGIN = 6.0
_NAME_FONT = theme.font(8, bold=True)
_PORT_FONT = theme.font(7)


def cell_title(cell: YosysCell) -> str:
    """The name of a cell's type on its block, like DFF_P or add"""
    return cell.component_type().strip("_")


class CellItem(QGraphicsItem):
    """A cell of the netlist: a gate as its symbol, else a block with its name and ports"""

    def __init__(self, name: str, cell: YosysCell) -> None:
        super().__init__()
        self._cell = cell
        self._inputs = [p for p in cell.connections if cell.port_directions.get(p) == "input"]
        self._outputs = [p for p in cell.connections if p not in self._inputs]
        self._symbol = GATE_SYMBOLS.get(cell.type)
        if self._symbol is not None:
            self._width = GATE_WIDTH
            self._height = max(len(self._inputs), 1) * PORT_DISTANCE
            self._input_ys = [
                PORT_DISTANCE / 2 + PORT_DISTANCE * i for i in range(len(self._inputs))
            ]
            self._output_ys = [self._height / 2] * len(self._outputs)
        else:
            names = QFontMetricsF(_PORT_FONT)
            title = QFontMetricsF(_NAME_FONT).horizontalAdvance(cell_title(cell))
            left = max((names.horizontalAdvance(p) for p in self._inputs), default=0.0)
            right = max((names.horizontalAdvance(p) for p in self._outputs), default=0.0)
            width = max(title + 2 * TEXT_MARGIN, left + right + 4 * TEXT_MARGIN, GATE_WIDTH)
            self._width = math.ceil(width / 10) * 10
            rows = max(len(self._inputs), len(self._outputs), 1)
            self._height = HEADER + rows * PORT_DISTANCE
            self._input_ys = [
                HEADER + PORT_DISTANCE / 2 + PORT_DISTANCE * i for i in range(len(self._inputs))
            ]
            self._output_ys = [
                HEADER + PORT_DISTANCE / 2 + PORT_DISTANCE * i for i in range(len(self._outputs))
            ]
        self.setToolTip(f"{cell.type} {name.lstrip(chr(92))}")
        self.setAcceptedMouseButtons(Qt.MouseButton.NoButton)

    def shape_of(self) -> NodeShape:
        """The size and the pins of the cell, for the layout"""
        pins = {port: (0.0, y) for port, y in zip(self._inputs, self._input_ys, strict=True)}
        pins.update(
            {
                port: (self._width, y)
                for port, y in zip(self._outputs, self._output_ys, strict=True)
            }
        )
        return NodeShape(self._width, self._height, pins)

    def boundingRect(self) -> QRectF:
        """QT function"""
        return QRectF(-2, -2, self._width + 4, self._height + 4)

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        """QT function"""
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(0, 0, self._width, self._height)
        if self._symbol is not None:
            shape, invert, exclusive = self._symbol
            paint_gate(painter, rect, shape, invert, exclusive, self._input_ys, self._height / 2)
            return
        theme.paint_body(painter, rect)
        painter.setPen(theme.ink_pen(1.0, theme.OFF))
        painter.drawLine(QPointF(4, HEADER - 4), QPointF(self._width - 4, HEADER - 4))
        theme.paint_text(
            painter, QRectF(0, 0, self._width, HEADER - 4), cell_title(self._cell), 8, bold=True
        )
        for ports, ys, align in (
            (self._inputs, self._input_ys, Qt.AlignmentFlag.AlignLeft),
            (self._outputs, self._output_ys, Qt.AlignmentFlag.AlignRight),
        ):
            for port, y in zip(ports, ys, strict=True):
                theme.paint_text(
                    painter,
                    QRectF(TEXT_MARGIN, y - 8, self._width - 2 * TEXT_MARGIN, 16),
                    port,
                    7,
                    align=align | Qt.AlignmentFlag.AlignVCenter,
                )


class NetlistViewScene(QGraphicsScene):
    """The cells and wires of a Verilog component's netlist, read-only"""

    def __init__(self, app_model: AppModel, component: YosysComponent) -> None:
        super().__init__()
        self._app_model = app_model
        self.component = component
        # The parts it was built for, the component builds new ones when it is reloaded
        self.parts: NetlistParts = component.netlist_parts()
        # The module ports, drawn with the values of the component's ports
        self._stand_in_circuit = Circuit()
        parts = self.parts
        # Not the cells that are not simulated (and have no component)
        cells = {name: cell for name, cell in parts.cells.items() if name in parts.components}
        self._build(netlist_graph(parts.ports, cells, parts.nets))

    def is_current(self, component: object) -> bool:
        """The scene shows a component as it is built now"""
        return (
            isinstance(component, YosysComponent)
            and component is self.component
            and component.netlist_parts() is self.parts
        )

    def _port_object(self, node: str, name: str) -> tuple[ComponentObject, NodeShape]:
        """An In, Out or InOut of the module, and its shape"""
        port = self.parts.ports[name]
        width = len(port.bits)
        circuit = self._stand_in_circuit
        stand_in: CircuitInput | CircuitOutput | CircuitInOut
        cls: type[ViewInput | ViewOutput | ViewInOut]
        if port.direction == "input":
            stand_in, cls = CircuitInput(circuit, label=name, width=width), ViewInput
        elif port.direction == "output":
            stand_in, cls = CircuitOutput(circuit, label=name, width=width), ViewOutput
        else:
            stand_in, cls = CircuitInOut(circuit, label=name, width=width), ViewInOut
        component_object = cls(self._app_model, stand_in, 0, 0)
        component_object.outer = self.component.port(name)
        component_object.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
        component_object.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        for item in [component_object, *component_object.childItems()]:
            item.setAcceptHoverEvents(False)
            item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        rect = QRectF(component_object.rect())
        pin = component_object.get_port_item(stand_in.port(name)).portPos() - rect.topLeft()
        return component_object, NodeShape(rect.width(), rect.height(), {name: (pin.x(), pin.y())})

    def _build(self, graph: NetlistGraph) -> None:
        shapes: dict[str, NodeShape] = {}
        items: dict[str, QGraphicsItem] = {}
        for node in graph.inputs + graph.outputs:
            items[node], shapes[node] = self._port_object(node, node.partition(":")[2])
        for node in graph.cells:
            cell_name = node.partition(":")[2]
            cell_item = CellItem(cell_name, self.parts.cells[cell_name])
            items[node], shapes[node] = cell_item, cell_item.shape_of()
        layout = netlist_layout(shapes, graph.inputs, graph.outputs, graph.wires)
        for node, item in items.items():
            x, y = layout.positions[node]
            if isinstance(item, ComponentObject):
                rect = item.rect()
                item.setPos(x - rect.x(), y - rect.y())
            else:
                item.setPos(x, y)
            self.addItem(item)
        for pin, text in graph.constants.items():
            self._constant(pin, text, layout.positions[pin.node], shapes[pin.node])
        dots = {source: junctions(segments) for source, segments in layout.trees().items()}
        wires: list[tuple[list[tuple[QPointF, QPointF]], list[QPointF], int]] = []
        for (source, sink), segments in layout.wires.items():
            points = {point for segment in segments for point in segment}
            wire_dots = [QPointF(*dot) for dot in dots[source] if dot in points]
            qsegments = [(QPointF(*start), QPointF(*end)) for start, end in segments]
            wires.append((qsegments, wire_dots, len(graph.wires[(source, sink)])))
        # Kept here: the scene doesn't keep a Python item alive
        self._lines_item = _WiresItem(wires)
        self.addItem(self._lines_item)

    def _constant(
        self, pin: Pin, text: str, position: tuple[float, float], shape: NodeShape
    ) -> None:
        """A constant on a pin, left of it"""
        item = QGraphicsSimpleTextItem(text)
        item.setFont(_PORT_FONT)
        item.setBrush(theme.MUTED)
        rect = item.boundingRect()
        px, py = shape.pins[pin.port]
        item.setPos(position[0] + px - rect.width() - 4, position[1] + py - rect.height())
        self.addItem(item)


class _WiresItem(QGraphicsItem):
    """
    The wires of the netlist, in the color of the ink: a bus thicker, with larger dots. The
    values are in the ports of the module, not on the wires.
    """

    def __init__(
        self, wires: list[tuple[list[tuple[QPointF, QPointF]], list[QPointF], int]]
    ) -> None:
        super().__init__()
        # For each wire: its segments, its dots, and its width in bits
        self._wires = wires
        rect = QRectF()
        for segments, _, _ in wires:
            for start, end in segments:
                rect = rect.united(QRectF(start, end).normalized())
        self._rect = rect.adjusted(-6, -6, 6, 6)
        self.setZValue(-1)
        self.setAcceptedMouseButtons(Qt.MouseButton.NoButton)

    def boundingRect(self) -> QRectF:
        """QT function"""
        return self._rect

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        """QT function"""
        for segments, dots, width in self._wires:
            bus = width > 1
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
            painter.setPen(QPen(theme.INK, 3 if bus else 1.5))
            for start, end in segments:
                painter.drawLine(start, end)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(theme.INK)
            radius = 3.5 if bus else 2.5
            for dot in dots:
                painter.drawEllipse(dot, radius, radius)
