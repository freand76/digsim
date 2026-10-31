# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""
A read-only view of the netlist of a Verilog component: its cells (gates drawn as their
symbols, other cells as blocks with their names) and the wires between them, laid out from
the inputs on the left to the outputs on the right. The ports show the values of the
simulation.
"""

from __future__ import annotations

import dataclasses
import math
from typing import TYPE_CHECKING

from PySide6.QtCore import QEvent, QObject, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFontMetricsF, QKeyEvent, QPainter, QPen
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QStyleOptionGraphicsItem,
    QVBoxLayout,
    QWidget,
)

from digsim.app._line_graph import junctions
from digsim.app._netlist_layout import NodeShape, netlist_layout
from digsim.app._netlist_search import entry_text, search_entries
from digsim.app.gui_objects import ComponentObject
from digsim.app.gui_objects import _theme as theme
from digsim.app.gui_objects._symbol_objects import paint_gate
from digsim.circuit import Circuit
from digsim.circuit.components import CircuitInOut, CircuitInput, CircuitOutput, YosysComponent
from digsim.circuit.components._yosys_component import NetlistParts
from digsim.utils import (
    NetlistEntry,
    NetlistGraph,
    Pin,
    YosysCell,
    cell_node,
    netlist_entries,
    netlist_graph,
)

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
# The color of the cells of the search entry that is selected. The rest is dimmed to this
# opacity.
HIGHLIGHT_COLOR = "#2d7ff9"
DIMMED = 0.25
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
        # The color of the search entry it is part of, see NetlistViewScene.highlight()
        self.highlight: QColor | None = None
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
        return QRectF(-7, -7, self._width + 14, self._height + 14)

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        """QT function"""
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(0, 0, self._width, self._height)
        if self.highlight is not None:
            # A glow of its color around it
            glow = QColor(self.highlight)
            glow.setAlpha(90)
            painter.setPen(QPen(self.highlight, 2))
            painter.setBrush(glow)
            painter.drawRoundedRect(rect.adjusted(-5, -5, 5, 5), 6, 6)
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
        # The items of the nodes, and the texts of the constants, see highlight()
        self._items: dict[str, QGraphicsItem] = {}
        self._constants: list[tuple[str, QGraphicsItem]] = []
        self._build(netlist_graph(parts.ports, cells, parts.nets))
        module = next(iter(component.netlist().modules.values()))
        # The signals, types of cells and source lines to search for
        self.entries = netlist_entries(module.netnames, cells, parts.nets)

    def highlight(self, cells: frozenset[str]) -> None:
        """
        Show cells (by name) in the highlight color, with the wires from them, and the
        rest dimmed. Nothing is dimmed without cells.
        """
        color = QColor(HIGHLIGHT_COLOR)
        colors = {cell_node(cell): color for cell in cells}
        dim = bool(colors)
        for node, item in self._items.items():
            if isinstance(item, CellItem):
                item.highlight = colors.get(node)
                item.update()
            item.setOpacity(DIMMED if dim and node not in colors else 1.0)
        for node, item in self._constants:
            item.setOpacity(DIMMED if dim and node not in colors else 1.0)
        self._lines_item.highlight(colors)

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
        self._items = items
        for pin, text in graph.constants.items():
            self._constant(pin, text, layout.positions[pin.node], shapes[pin.node])
        dots = {source: junctions(segments) for source, segments in layout.trees().items()}
        wires: list[_Wire] = []
        for (source, sink), segments in layout.wires.items():
            points = {point for segment in segments for point in segment}
            wire_dots = [QPointF(*dot) for dot in dots[source] if dot in points]
            qsegments = [(QPointF(*start), QPointF(*end)) for start, end in segments]
            width = len(graph.wires[(source, sink)])
            wires.append(_Wire(qsegments, wire_dots, width, source.node, sink.node))
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
        self._constants.append((pin.node, item))


@dataclasses.dataclass
class _Wire:
    """A wire of the view: its segments and dots, its width in bits, and its two nodes"""

    segments: list[tuple[QPointF, QPointF]]
    dots: list[QPointF]
    width: int
    source: str
    sink: str


class _WiresItem(QGraphicsItem):
    """
    The wires of the netlist, in the color of the ink: a bus thicker, with larger dots. The
    values are in the ports of the module, not on the wires. A wire from a highlighted
    node has its color (the signal of the node), a wire to one is drawn as it is, and the
    others are dimmed then.
    """

    def __init__(self, wires: list[_Wire]) -> None:
        super().__init__()
        self._wires = wires
        self._colors: dict[str, QColor] = {}
        rect = QRectF()
        for wire in wires:
            for start, end in wire.segments:
                rect = rect.united(QRectF(start, end).normalized())
        self._rect = rect.adjusted(-6, -6, 6, 6)
        self.setZValue(-1)
        self.setAcceptedMouseButtons(Qt.MouseButton.NoButton)

    def highlight(self, colors: dict[str, QColor]) -> None:
        """The colors of the highlighted nodes, see NetlistViewScene.highlight()"""
        self._colors = colors
        self.update()

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
        dimmed = QColor(theme.INK)
        dimmed.setAlphaF(DIMMED)
        # The highlighted wires on top
        wires = sorted(
            self._wires,
            key=lambda wire: (wire.source in self._colors, wire.sink in self._colors),
        )
        for wire in wires:
            color = self._colors.get(wire.source)
            if color is None:
                into = wire.sink in self._colors or not self._colors
                color = QColor(theme.INK) if into else dimmed
            bus = wire.width > 1
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
            painter.setPen(QPen(color, 3 if bus else 1.5))
            for start, end in wire.segments:
                painter.drawLine(start, end)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            radius = 3.5 if bus else 2.5
            for dot in wire.dots:
                painter.drawEllipse(dot, radius, radius)


class NetlistSearchPane(QWidget):
    """
    The search of a netlist view: a field, and the list of the signals, types of cells and
    source lines that match it (all of them when it is empty). The cells of the selected
    entry are shown in the view, or of the only one that matches.
    """

    sig_highlight = Signal(frozenset)

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 0, 4)
        self.field = QLineEdit(self)
        self.field.setPlaceholderText("Search signals, cells, lines (Ctrl+F)")
        self.field.setClearButtonEnabled(True)
        self.field.installEventFilter(self)
        layout.addWidget(self.field)
        self.list = QListWidget(self)
        self.list.installEventFilter(self)
        layout.addWidget(self.list, 1)
        self._entries: list[NetlistEntry] = []
        self.field.textChanged.connect(self._fill)
        self.list.itemSelectionChanged.connect(self._show)

    def set_entries(self, entries: list[NetlistEntry]) -> None:
        """The entries of a netlist (built again)"""
        self._entries = entries
        self._fill()

    def _fill(self) -> None:
        """The entries that match the field, none selected"""
        self.list.clear()
        for entry in search_entries(self.field.text(), self._entries):
            item = QListWidgetItem(entry_text(entry))
            item.setData(Qt.ItemDataRole.UserRole, entry)
            item.setToolTip(entry_text(entry))
            self.list.addItem(item)
        self._show()

    def _show(self) -> None:
        """The cells of the selected entry, or of the only one that matches, in the view"""
        selected = self.list.selectedItems()
        if not selected and self.list.count() == 1 and self.field.text().strip():
            selected = [self.list.item(0)]
        cells = selected[0].data(Qt.ItemDataRole.UserRole).cells if selected else frozenset()
        self.sig_highlight.emit(cells)

    def clear(self) -> None:
        """No search, nothing shown"""
        self.field.clear()
        self.list.clearSelection()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """
        QT function: Esc clears, Enter selects the best match, Down goes from the field to
        the list
        """
        if event.type() == QEvent.Type.KeyPress:
            assert isinstance(event, QKeyEvent)
            key = event.key()
            if key == Qt.Key.Key_Escape:
                self.clear()
                self.field.setFocus()
                return True
            enter = key in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
            if watched is self.field and (enter or key == Qt.Key.Key_Down) and self.list.count():
                self.list.setCurrentRow(0)
                if key == Qt.Key.Key_Down:
                    self.list.setFocus()
                return True
        return super().eventFilter(watched, event)
