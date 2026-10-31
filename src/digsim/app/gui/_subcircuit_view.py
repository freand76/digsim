# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""
A read-only view of a subcircuit instance: the parts of one subcircuit, drawn like its file,
with the values of the simulation of the circuit it is in
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import (
    QBrush,
    QKeySequence,
    QMouseEvent,
    QPainter,
    QResizeEvent,
    QShortcut,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsScene,
    QGraphicsSceneContextMenuEvent,
    QGraphicsSceneMouseEvent,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QMenu,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

import digsim.app.gui_objects
from digsim.app._line_graph import junctions
from digsim.app.gui_objects import ComponentObject
from digsim.app.gui_objects import _theme as theme
from digsim.circuit import Circuit
from digsim.circuit.components import (
    CircuitInOut,
    CircuitInput,
    CircuitOutput,
    CircuitPort,
    SubCircuit,
    YosysComponent,
)
from digsim.circuit.components.atoms import Component, Port
from digsim.storage_model import LineDataClass

from ._netlist_view import NetlistSearchPane, NetlistViewScene
from ._top_bar import SimControlWidget, SimTimeWidget
from ._view_items import (
    LinesItem,
    OuterPortValue,
    ViewInOut,
    ViewInput,
    ViewOutput,
)


if TYPE_CHECKING:
    from digsim.app.model import AppModel

# The width of the search of a netlist view
SEARCH_WIDTH = 280
# The margin around the parts when the view fits them, and the most it zooms in
FIT_MARGIN = 20
FIT_MAX = 2.0


def can_view(component: Component) -> bool:
    """A component has a view: a subcircuit (drawn like its file), or a Verilog component"""
    if isinstance(component, SubCircuit):
        return component.has_layout()
    return isinstance(component, YosysComponent)


def view_action_text(component: Component) -> str:
    """The context menu action that shows the view of a component"""
    return "View Netlist" if isinstance(component, YosysComponent) else "View Subcircuit"


def find_instance(circuit: Circuit, names: list[str]) -> SubCircuit | YosysComponent | None:
    """
    A subcircuit or Verilog component by its chain of names: the name of a component of the
    circuit, then the names in the files of the subcircuits it is in. None if it is gone.
    """
    component: Component | None = None
    for index, name in enumerate(names):
        if index == 0:
            component = next(
                (c for c in circuit.get_toplevel_components() if c.name() == name), None
            )
        elif isinstance(component, SubCircuit):
            component = component.part(name)
        else:
            return None
    return component if isinstance(component, (SubCircuit, YosysComponent)) else None


class SubCircuitViewScene(QGraphicsScene):
    """
    The parts of a subcircuit, where they are in its file, read-only. A subcircuit part
    has View Subcircuit in its context menu, and a Verilog part View Netlist, to look inside
    them too.
    """

    def __init__(
        self,
        app_model: AppModel,
        subcircuit: SubCircuit,
        open_view: Callable[[Component], None],
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
            CircuitInput.DIRECTION: ViewInput,
            CircuitOutput.DIRECTION: ViewOutput,
            CircuitInOut.DIRECTION: ViewInOut,
        }
        for file_port in subcircuit.file_ports():
            position = layout.gui.get(file_port.component)
            if position is None:
                continue
            object_class = classes[file_port.direction]
            stand_in = self._stand_in(file_port.direction, file_port.label, file_port.width)
            component_object = self._add_object(stand_in, position, object_class)
            outer = subcircuit.outer_port(file_port.label)
            assert isinstance(component_object, OuterPortValue)
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
        # Kept here: the scene doesn't keep a Python item alive, and when the last reference
        # to it went (like in part_object()) the lines were deleted
        self._lines_item = LinesItem([self._line(line, stand_ins) for line in layout.lines])
        self.addItem(self._lines_item)

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

    def is_current(self, component: Component) -> bool:
        """The scene shows a subcircuit as it is built now"""
        return component is self.subcircuit and self.parts == self.subcircuit.parts()

    def part_object(self, pos: QPointF) -> ComponentObject | None:
        """The subcircuit or Verilog part at a place"""
        for item in self.items(pos):
            while item is not None and not isinstance(item, ComponentObject):
                item = item.parentItem()
            if item is not None and isinstance(item.component, (SubCircuit, YosysComponent)):
                return item
        return None

    def mouseDoubleClickEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """QT function: a double-click on a subcircuit or Verilog part views it"""
        component_object = self.part_object(event.scenePos())
        if event.button() == Qt.MouseButton.LeftButton and component_object is not None:
            if can_view(component_object.component):
                self._open_view(component_object.component)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event: QGraphicsSceneContextMenuEvent) -> None:
        """QT function: View Subcircuit or View Netlist on a part"""
        component_object = self.part_object(event.scenePos())
        if component_object is None:
            return
        part = component_object.component
        menu = QMenu()
        action = menu.addAction(view_action_text(part))
        action.setEnabled(can_view(part))
        action.triggered.connect(lambda: self._open_view(part))
        menu.exec(event.screenPos())
        event.accept()

    def parts_name(self, part: Component) -> str | None:
        """The name in the file of a part of this subcircuit"""
        for name in self.subcircuit.layout().gui:
            if self.subcircuit.part(name) is part:
                return name
        return None


class SubCircuitView(QGraphicsView):
    """
    The view of a subcircuit's scene, zoomed to fit when it is shown. A drag with the
    mouse pans it, the wheel and the zoom shortcuts zoom.
    """

    ZOOM_IN_FACTOR = 1.25
    ZOOM_OUT_FACTOR = 0.8

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.refresh_theme()
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        # The hand cursor, like Shift in the circuit area. The parts take no mouse buttons,
        # a drag pans on them too.
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        # Moves without a button too, for the arrow over a part that can be viewed
        self.viewport().setMouseTracking(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # It fits the parts when it gets a size, until it is zoomed or panned
        self._zoomed = False

    def refresh_theme(self) -> None:
        """The background in the color of the theme, after it changed"""
        self.setBackgroundBrush(QBrush(theme.BACKGROUND))
        self.viewport().update()

    def resizeEvent(self, event: QResizeEvent) -> None:
        """QT function"""
        super().resizeEvent(event)
        if self._zoomed:
            self._update_scene_rect()
        else:
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
        self._update_scene_rect()
        self.centerOn(rect.center())

    def zoom_fit(self) -> None:
        """View > Zoom to Fit: fit the parts, also when the view gets another size"""
        self._zoomed = False
        self.fit()

    def zoom_in(self) -> None:
        """View > Zoom In"""
        self._zoom(self.ZOOM_IN_FACTOR)

    def zoom_out(self) -> None:
        """View > Zoom Out"""
        self._zoom(self.ZOOM_OUT_FACTOR)

    def _zoom(self, factor: float) -> None:
        self._zoomed = True
        self.scale(factor, factor)
        self._update_scene_rect()

    def _update_scene_rect(self) -> None:
        """
        The parts with a visible area of room around them: the view pans until they are
        at an edge. The scene would otherwise be the parts, which can't pan when they fit.
        """
        scene = self.scene()
        if scene is None:
            return
        visible = self.mapToScene(self.viewport().rect()).boundingRect()
        center = self.mapToScene(self.viewport().rect().center())
        self.setSceneRect(
            scene.itemsBoundingRect().adjusted(
                -visible.width(), -visible.height(), visible.width(), visible.height()
            )
        )
        self.centerOn(center)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """QT function: a drag pans, the view stays there when it gets another size"""
        if event.buttons() & Qt.MouseButton.LeftButton:
            self._zoomed = True
        super().mouseMoveEvent(event)
        if event.buttons() == Qt.MouseButton.NoButton:
            self._update_cursor(event.position().toPoint())

    def _update_cursor(self, pos: QPoint) -> None:
        """An arrow over a part that can be viewed (a double-click), else the hand"""
        scene = self.scene()
        component_object = (
            scene.part_object(self.mapToScene(pos))
            if isinstance(scene, SubCircuitViewScene)
            else None
        )
        viewable = component_object is not None and can_view(component_object.component)
        self.viewport().setCursor(
            Qt.CursorShape.ArrowCursor if viewable else Qt.CursorShape.OpenHandCursor
        )

    def wheelEvent(self, event: QWheelEvent) -> None:
        """QT function: the wheel zooms"""
        self._zoom(self.ZOOM_IN_FACTOR if event.angleDelta().y() > 0 else self.ZOOM_OUT_FACTOR)
        event.accept()


class ViewTab(QWidget):
    """
    A tab with a read-only view of a subcircuit instance, or of the netlist of a Verilog
    component, in the simulation of the circuit of another tab (its model): the simulation
    goes on when the tab is shown
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
        # A netlist has its search on the left of the view
        splitter = QSplitter(self)
        self.search = NetlistSearchPane(splitter)
        self.view = SubCircuitView(splitter)
        splitter.addWidget(self.search)
        splitter.addWidget(self.view)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([SEARCH_WIDTH, 1000])
        layout.addWidget(splitter, 1)
        self.search.sig_highlight.connect(self._highlight)
        QShortcut(QKeySequence("Ctrl+F"), self, self._focus_search).setContext(
            Qt.ShortcutContext.WidgetWithChildrenShortcut
        )
        self._scene: SubCircuitViewScene | NetlistViewScene | None = None
        self.refresh()
        app_model.sig_repaint.connect(self._repaint)
        app_model.sig_sim_time_notify.connect(self._repaint)
        app_model.sig_synchronize_gui.connect(self.refresh)
        app_model.sig_control_notify.connect(self.refresh)

    @property
    def instance(self) -> SubCircuit | YosysComponent | None:
        """The subcircuit or Verilog component, None if it is gone"""
        return find_instance(self.app_model.objects.circuit, self.names)

    def title(self) -> str:
        return " > ".join(self.names)

    def refresh(self) -> None:
        """Build the scene again when the instance was built again, or is gone"""
        instance = self.instance
        if self._scene is not None and instance is not None and self._scene.is_current(instance):
            return
        if instance is None:
            self._label.setText(f"{self.title()}: it is gone")
            self.view.setScene(QGraphicsScene(self))
            self._scene = None
            return
        self.search.setVisible(isinstance(instance, YosysComponent))
        if isinstance(instance, YosysComponent):
            self._scene = NetlistViewScene(self.app_model, instance)
            self.search.set_entries(self._scene.entries)
            source = instance.source_file
            name = Path(source).name if source is not None else instance.module_name()
            kind = "functional blocks" if instance.functional else "gates"
            about = f"{name}, {kind}"
        else:
            self._scene = SubCircuitViewScene(self.app_model, instance, self._view_part)
            about = instance.source_file().name
        self.view.setScene(self._scene)
        self.view.fit()
        self._label.setText(
            f"  {self.title()} ({about}), read-only: the values of the simulation of its circuit"
        )

    def _highlight(self, cells: frozenset[str]) -> None:
        if isinstance(self._scene, NetlistViewScene):
            self._scene.highlight(cells)

    def _focus_search(self) -> None:
        if self.search.isVisible():
            self.search.field.setFocus()
            self.search.field.selectAll()

    def _view_part(self, part: Component) -> None:
        if not isinstance(self._scene, SubCircuitViewScene):
            return
        name = self._scene.parts_name(part)
        if name is not None:
            self._open_view(self.app_model, [*self.names, name])

    def _repaint(self, *_: object) -> None:
        if self._scene is not None:
            self._scene.update()
