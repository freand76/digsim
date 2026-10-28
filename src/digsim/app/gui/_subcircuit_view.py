# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""
A read-only view of a subcircuit instance: the parts of one subcircuit, drawn like its file,
with the values of the simulation of the circuit it is in
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QResizeEvent, QWheelEvent
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsScene,
    QGraphicsSceneContextMenuEvent,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QMenu,
    QStyleOptionGraphicsItem,
    QVBoxLayout,
    QWidget,
)

import digsim.app.gui_objects
from digsim.app._line_graph import junctions
from digsim.app._value_text import value_text
from digsim.app.gui_objects import ComponentObject
from digsim.app.gui_objects import _theme as theme
from digsim.app.gui_objects._circuit_port_object import (
    CircuitInOutObject,
    CircuitInputObject,
    CircuitOutputObject,
)
from digsim.circuit import Circuit
from digsim.circuit.components import (
    CircuitInOut,
    CircuitInput,
    CircuitOutput,
    CircuitPort,
    SubCircuit,
)
from digsim.circuit.components.atoms import VALUE_TYPE, Component, Port, PortInOut
from digsim.storage_model import LineDataClass

from ._top_bar import SimControlWidget, SimTimeWidget


if TYPE_CHECKING:
    from digsim.app.model import AppModel

# The margin around the parts when the view fits them, and the most it zooms in
FIT_MARGIN = 20
FIT_MAX = 2.0


def find_instance(circuit: Circuit, names: list[str]) -> SubCircuit | None:
    """
    A subcircuit by its chain of names: the name of a subcircuit of the circuit, then the
    names in the files of the subcircuits in it. None if it is gone.
    """
    component: Component | None = None
    for index, name in enumerate(names):
        if index == 0:
            component = next(
                (c for c in circuit.get_toplevel_components() if c.name() == name), None
            )
        elif isinstance(component, SubCircuit):
            component = component.part(name)
        if not isinstance(component, SubCircuit):
            return None
    return component if isinstance(component, SubCircuit) else None


def _port_value(port: Port) -> VALUE_TYPE:
    """The value on a port's wire: what an inout port reads, the value of other ports"""
    if isinstance(port, PortInOut):
        return port.read_value()
    return port.value


class _OuterPortValue:
    """A circuit port drawn in a view, with the value of the subcircuit's port"""

    outer: Port
    _component: Component

    def _texts(self) -> tuple[str, str]:
        port = self._component
        assert isinstance(port, CircuitPort)
        return port.label(), value_text(_port_value(self.outer), port.width)


class _ViewInput(_OuterPortValue, CircuitInputObject):
    """An In of the subcircuit, with the value that drives the subcircuit's input"""


class _ViewOutput(_OuterPortValue, CircuitOutputObject):
    """An Out of the subcircuit, with the value of the subcircuit's output"""


class _ViewInOut(_OuterPortValue, CircuitInOutObject):
    """An InOut of the subcircuit, with the value of the wire of its inout port"""


class _LinesItem(QGraphicsItem):
    """
    The lines of the subcircuit's file, each with the value of its wire: the value a
    port on it reads, colored like the wires of the circuit area
    """

    def __init__(
        self, lines: list[tuple[list[tuple[QPointF, QPointF]], list[QPointF], Port | None]]
    ) -> None:
        super().__init__()
        # For each line: its segments, its dots, and the port whose value it has
        self._lines = lines
        rect = QRectF()
        for segments, _, _ in lines:
            for start, end in segments:
                rect = rect.united(QRectF(start, end).normalized())
        self._rect = rect.adjusted(-6, -6, 6, 6)
        self.setZValue(-1)
        self.setAcceptedMouseButtons(Qt.MouseButton.NoButton)

    def boundingRect(self) -> QRectF:
        """QT function"""
        return self._rect

    @staticmethod
    def _color(value: VALUE_TYPE, width: int) -> QColor:
        if value == "X":
            return QColor(theme.WIRE_X)
        if value == "Z":
            return QColor(theme.WIRE_Z)
        if not isinstance(value, int) or value == 0:
            return QColor(theme.WIRE)
        return theme.dim(theme.ON, 0.4 + 0.6 * value / (2**width - 1), theme.WIRE)

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        """QT function"""
        for segments, dots, port in self._lines:
            width = port.width if port is not None else 1
            color = self._color(_port_value(port) if port is not None else "Z", width)
            pen = QPen(color, 4 if width > 1 else 2)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
            painter.setPen(pen)
            for start, end in segments:
                painter.drawLine(start, end)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            for dot in dots:
                painter.drawEllipse(dot, 4 if width > 1 else 3, 4 if width > 1 else 3)


class SubCircuitViewScene(QGraphicsScene):
    """
    The parts of a subcircuit, where they are in its file, read-only. A subcircuit part
    has View Subcircuit in its context menu, to look inside it too.
    """

    def __init__(
        self,
        app_model: AppModel,
        subcircuit: SubCircuit,
        open_view: Callable[[SubCircuit], None],
    ) -> None:
        super().__init__()
        self._app_model = app_model
        self._open_view = open_view
        self.subcircuit = subcircuit
        # The parts it was built for, a reload of the subcircuit builds new ones
        self.parts = subcircuit.parts()
        self._objects: dict[Component, ComponentObject] = {}
        # The circuit ports of the file, drawn with the values of the subcircuit's ports
        self._stand_in_circuit = Circuit()
        self._build()

    def _add_object(
        self, component: Component, position: Any, cls: type[ComponentObject]
    ) -> ComponentObject:
        component_object = cls(self._app_model, component, position.x, position.y)
        component_object.zlevel = position.z
        component_object.rotation_angle = position.rotation
        component_object.flipped = position.flipped
        # Read-only: not moved, selected or clicked, also not its ports
        component_object.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
        component_object.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        for item in [component_object, *component_object.childItems()]:
            item.setAcceptHoverEvents(False)
            item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.addItem(component_object)
        self._objects[component] = component_object
        return component_object

    def _build(self) -> None:
        subcircuit = self.subcircuit
        layout = subcircuit.layout()
        stand_ins: dict[str, tuple[ComponentObject, Port, Port]] = {}
        classes: dict[str, type[ComponentObject]] = {
            CircuitInput.DIRECTION: _ViewInput,
            CircuitOutput.DIRECTION: _ViewOutput,
            CircuitInOut.DIRECTION: _ViewInOut,
        }
        for file_port in subcircuit.file_ports():
            position = layout.gui.get(file_port.component)
            if position is None:
                continue
            object_class = classes[file_port.direction]
            stand_in = self._stand_in(file_port.direction, file_port.label, file_port.width)
            component_object = self._add_object(stand_in, position, object_class)
            outer = subcircuit.outer_port(file_port.label)
            assert isinstance(component_object, _OuterPortValue)
            component_object.outer = outer
            stand_ins[file_port.component] = (
                component_object,
                stand_in.port(file_port.label),
                outer,
            )
        for name, position in layout.gui.items():
            part = subcircuit.part(name)
            if part is None:
                continue
            cls = digsim.app.gui_objects.class_factory(type(part).__name__)
            self._add_object(part, position, cls)
        self.addItem(_LinesItem([self._line(line, stand_ins) for line in layout.lines]))

    def _stand_in(self, direction: str, label: str, width: int) -> CircuitPort:
        """A circuit port in a circuit of its own, it is only drawn"""
        circuit = self._stand_in_circuit
        if direction == CircuitInput.DIRECTION:
            return CircuitInput(circuit, label=label, width=width)
        if direction == CircuitOutput.DIRECTION:
            return CircuitOutput(circuit, label=label, width=width)
        return CircuitInOut(circuit, label=label, width=width)

    def _line(
        self, line: LineDataClass, stand_ins: dict[str, tuple[ComponentObject, Port, Port]]
    ) -> tuple[list[tuple[QPointF, QPointF]], list[QPointF], Port | None]:
        """The segments and dots of a line, and the port whose value it has"""
        places: dict[str, QPointF] = {
            key: QPointF(point[0], point[1]) for key, point in line.points.items()
        }
        readers: list[Port] = []
        drivers: list[Port] = []
        for key in line.ports:
            component_name, _, port_name = key.rpartition(".")
            if component_name in stand_ins:
                component_object, port, outer = stand_ins[component_name]
                places[key] = component_object.get_port_item(port).portPos()
                # The subcircuit's output reads the line, its input drives it
                (readers if outer.is_output() else drivers).append(outer)
                continue
            part = self.subcircuit.part(component_name)
            if part is None or part not in self._objects:
                continue
            port = part.port(port_name)
            places[key] = self._objects[part].get_port_item(port).portPos()
            (readers if port.is_input() else drivers).append(port)
        segments = [
            (places[first], places[second])
            for first, second in line.segments
            if first in places and second in places
        ]
        points = [((s.x(), s.y()), (e.x(), e.y())) for s, e in segments]
        dots = [QPointF(x, y) for x, y in junctions(points)]
        # A port that reads the line has its value, all its drivers resolved
        value_port = readers[0] if readers else drivers[0] if drivers else None
        return segments, dots, value_port

    def subcircuit_object(self, pos: QPointF) -> ComponentObject | None:
        for item in self.items(pos):
            while item is not None and not isinstance(item, ComponentObject):
                item = item.parentItem()
            if item is not None and isinstance(item.component, SubCircuit):
                return item
        return None

    def contextMenuEvent(self, event: QGraphicsSceneContextMenuEvent) -> None:
        """QT function: View Subcircuit on a subcircuit part"""
        component_object = self.subcircuit_object(event.scenePos())
        if component_object is None:
            return
        part = component_object.component
        assert isinstance(part, SubCircuit)
        menu = QMenu()
        action = menu.addAction("View Subcircuit")
        action.setEnabled(part.has_layout())
        action.triggered.connect(lambda: self._open_view(part))
        menu.exec(event.screenPos())
        event.accept()

    def parts_name(self, part: SubCircuit) -> str | None:
        """The name in the file of a subcircuit part of this subcircuit"""
        for name in self.subcircuit.layout().gui:
            if self.subcircuit.part(name) is part:
                return name
        return None


class SubCircuitView(QGraphicsView):
    """The view of a subcircuit's scene, zoomed to fit when it is shown"""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setBackgroundBrush(theme.BACKGROUND)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        # It fits the parts when it gets a size, until the wheel zooms
        self._zoomed = False

    def resizeEvent(self, event: QResizeEvent) -> None:
        """QT function"""
        super().resizeEvent(event)
        if not self._zoomed:
            self.fit()

    def fit(self) -> None:
        scene = self.scene()
        if scene is None:
            return
        rect = scene.itemsBoundingRect().adjusted(-FIT_MARGIN, -FIT_MARGIN, FIT_MARGIN, FIT_MARGIN)
        self.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)
        if self.transform().m11() > FIT_MAX:
            self.resetTransform()
            self.scale(FIT_MAX, FIT_MAX)
            self.centerOn(rect.center())

    def wheelEvent(self, event: QWheelEvent) -> None:
        """QT function: the wheel zooms"""
        factor = 1.25 if event.angleDelta().y() > 0 else 0.8
        self._zoomed = True
        self.scale(factor, factor)
        event.accept()


class ViewTab(QWidget):
    """
    A tab with a read-only view of a subcircuit instance, in the simulation of the circuit
    of another tab (its model): the simulation goes on when the tab is shown
    """

    def __init__(
        self,
        app_model: AppModel,
        names: list[str],
        parent_tab: QWidget,
        open_view: Callable[[AppModel, list[str]], None],
        window: QWidget,
    ) -> None:
        super().__init__(window)
        self.app_model = app_model
        self.names = names
        self.parent_tab = parent_tab
        self._open_view = open_view
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        bar = QWidget(self)
        bar_layout = QHBoxLayout(bar)
        bar_layout.addWidget(SimControlWidget(app_model, bar))
        bar_layout.addWidget(SimTimeWidget(app_model, bar))
        self._label = QLabel(bar)
        bar_layout.addWidget(self._label, 1)
        layout.addWidget(bar)
        self.view = SubCircuitView(self)
        layout.addWidget(self.view, 1)
        self._scene: SubCircuitViewScene | None = None
        self.refresh()
        app_model.sig_repaint.connect(self._repaint)
        app_model.sig_sim_time_notify.connect(self._repaint)
        app_model.sig_synchronize_gui.connect(self.refresh)
        app_model.sig_control_notify.connect(self.refresh)

    @property
    def subcircuit(self) -> SubCircuit | None:
        """The instance, None if it is gone"""
        return find_instance(self.app_model.objects.circuit, self.names)

    def title(self) -> str:
        return " > ".join(self.names)

    def refresh(self) -> None:
        """Build the scene again when the instance was built again, or is gone"""
        subcircuit = self.subcircuit
        if (
            self._scene is not None
            and subcircuit is not None
            and self._scene.subcircuit is subcircuit
            and self._scene.parts == subcircuit.parts()
        ):
            return
        if subcircuit is None:
            self._label.setText(f"{self.title()}: the subcircuit is gone")
            self.view.setScene(QGraphicsScene(self))
            self._scene = None
            return
        self._scene = SubCircuitViewScene(self.app_model, subcircuit, self._view_part)
        self.view.setScene(self._scene)
        self.view.fit()
        self._label.setText(
            f"  {self.title()} ({subcircuit.source_file().name}), read-only: the values of "
            "the simulation of its circuit"
        )

    def _view_part(self, part: SubCircuit) -> None:
        if self._scene is None:
            return
        name = self._scene.parts_name(part)
        if name is not None:
            self._open_view(self.app_model, [*self.names, name])

    def _repaint(self, *_: object) -> None:
        if self._scene is not None:
            self._scene.update()
