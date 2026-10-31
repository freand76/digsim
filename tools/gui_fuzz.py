# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""
A randomized test of the GUI circuit editor, run offscreen with real mouse events

It builds a circuit from scratch: it adds components, draws wires (single bits and buses,
from output and input ports, with corners, and from corners of other wires), selects and
deletes wires, wire trees and components, drags, splits and merges segments, moves
components, zooms, undoes and redoes, saves and loads the circuit with the Save and Load
buttons, loads the example circuits, clears the circuit, and runs the simulation (with
Start, Stop, Single Step and Reset, with and without a VCD file, clicking buttons and
switches). After each step it checks that the GUI matches the circuit, that exactly what
should change, changed, and that the wires are painted where nothing covers them. The
window has a random size: in a small one the view scrolls. Components are added through
the model, like the GUI does after its settings dialog.

    uv run python tools/gui_fuzz.py                  # random seed, printed
    uv run python tools/gui_fuzz.py --seed 7 --steps 500 -v
    uv run python tools/gui_fuzz.py --seeds 1,2,3 --max-components 40

The output is one line when all is well. On a failure it prints the seed, the step, the
last actions and the failed check, saves the circuit, and exits with status 1. A run with
the same seed repeats the same actions.
"""

from __future__ import annotations

import argparse
import math
import os
import random
import subprocess
import sys
import tempfile
import time
from collections import Counter
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from itertools import pairwise
from pathlib import Path
from typing import Any, ClassVar

from PySide6.QtCore import (
    QEvent,
    QEventLoop,
    QMessageLogContext,
    QPointF,
    Qt,
    QTimer,
    QtMsgType,
    qInstallMessageHandler,
)
from PySide6.QtGui import QContextMenuEvent, QImage, QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QFileDialog, QGraphicsItem, QMenu

from digsim.app._line_graph import on_segment
from digsim.app._wire_key import Wire, drawn_key, port_key, wire_key
from digsim.app._wire_lines import Lines, Node
from digsim.app._wire_path import (
    X_OFFSET,
    arrival_offset,
    corner_directions,
    drawing_points,
    exits_vertically,
    is_forwards,
)
from digsim.app._wire_route import faces_vertically
from digsim.app.gui import MainWindow
from digsim.app.gui._circuit_area import (
    CircuitArea,
    NewWireGraphicsItem,
    WireGraphicsItem,
    WirePartGraphicsItem,
)
from digsim.app.gui._menu_bar import MenuBar
from digsim.app.gui._top_bar import SimControlWidget, VcdControlWidget
from digsim.app.gui_objects import ComponentObject
from digsim.app.gui_objects import _theme as theme
from digsim.app.gui_objects._component_port_item import PortGraphicsItem
from digsim.app.model import AppModel
from digsim.circuit.components.atoms import Port


# The GUI example circuits, also for a subcircuit among the components
EXAMPLE_CIRCUITS_FOLDER = Path(__file__).parent.parent / "circuits"
# Components with single bit and bus ports, and their settings
COMPONENTS: list[tuple[str, dict[str, Any]]] = [
    ("PushButton", {}),
    ("OnOffSwitch", {}),
    ("Led", {}),
    ("NOT", {}),
    ("AND", {"ports": 2}),
    ("OR", {"ports": 3}),
    ("XOR", {"ports": 2}),
    ("DFF", {"width": 1}),
    ("DFF", {"width": 4}),
    ("StaticValue", {"width": 4, "value": 5}),
    ("GND", {}),
    ("VDD", {}),
    ("LedBar", {"width": 4}),
    ("HexDigit", {"digits": 1, "dot": False}),
    ("HD44780", {}),
    ("Wires2Bus", {"width": 4}),
    ("Bus2Wires", {"width": 4}),
    ("Splitter", {"groups": [1, 3]}),
    ("Splitter", {"groups": [2, 2], "direction": "merge"}),
    ("TristateBuffer", {"width": 1}),
    ("TristateBuffer", {"width": 1}),
    ("TristateBuffer", {"width": 4}),
    ("TristateBuffer", {"width": 4}),
    ("RAM", {"address_width": 4, "data_width": 4, "mode": "async"}),
    ("Probe", {"width": 1}),
    ("Probe", {"width": 4, "radix": "bin"}),
    ("Adder", {"width": 4}),
    ("Counter", {"width": 4, "enable": True}),
    ("Decoder", {"select": 2}),
    ("SubCircuit", {"path": str(EXAMPLE_CIRCUITS_FOLDER / "subcircuits" / "half_adder.circuit")}),
]
# Components are placed in the cells of a grid, so that they don't overlap
GRID_COLUMNS, GRID_ROWS = 6, 4
CELL_WIDTH, CELL_HEIGHT = 240, 200
MAX_COMPONENTS = 14
UNDO_DEPTH = 100
# Window sizes: the smaller ones don't show the whole circuit, the view scrolls
WINDOW_SIZES = [(1700, 1100), (1200, 800), (900, 650)]
# The background of the circuit area, and the dots of its grid
BACKGROUND = {
    (color.red(), color.green(), color.blue()) for color in (theme.BACKGROUND, theme.GRID)
}
EXAMPLE_CIRCUITS = sorted(EXAMPLE_CIRCUITS_FOLDER.glob("*/*.circuit"))


class FuzzFailure(Exception):
    """A check failed"""


class Skip(Exception):
    """The action can't be done in this state, like a click that would hit another item"""


def check(condition: bool, message: str) -> None:
    """Fail with a message"""
    if not condition:
        raise FuzzFailure(message)


def simplify(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """
    The corners of a line, without repeated points, points in the middle of a line, and
    stubs where the line goes back the way it came
    """
    result: list[tuple[float, float]] = []
    for point in [(round(x, 1), round(y, 1)) for x, y in points]:
        while len(result) >= 2:
            (x1, y1), (x2, y2) = result[-2], result[-1]
            if not (x1 == x2 == point[0] or y1 == y2 == point[1]):
                break
            result.pop()
        if result and result[-1] == point:
            continue
        result.append(point)
    return result


class GuiFuzzer:
    """Random actions in the GUI, with a check after each"""

    def __init__(self, seed: int, verbose: bool, out_dir: Path) -> None:
        self.rng = random.Random(seed)
        self.seed = seed
        self.verbose = verbose
        self.out_dir = out_dir
        self.app = QApplication.instance() or QApplication([])
        self.model = AppModel()
        self.window = MainWindow(self.model, str(out_dir))
        self.window.resize(*self.rng.choice(WINDOW_SIZES))
        self.window.show()
        area = self.window.findChild(CircuitArea)
        assert area is not None
        self.area = area
        self.errors: list[str] = []
        self.model.sig_error.connect(self.errors.append)
        # Error dialogs are closed, as if the user clicked OK
        self.closer = QTimer()
        self.closer.timeout.connect(self._close_dialogs)
        self.closer.start(50)
        self.log: list[str] = []
        self.counts: Counter[str] = Counter()
        # Snapshots for undo and redo, like the model's stacks
        self.history: list[Any] = []
        self.future: list[Any] = []
        self.free_cells = [(col, row) for col in range(GRID_COLUMNS) for row in range(GRID_ROWS)]
        self.vcd_files = 0
        # The most components the circuit had
        self.most = 0
        self.spin(200)

    def close(self) -> None:
        """
        Close the window before Python exits: taken apart at exit, in no order, queued
        signals of the model reach a scene that is gone, and Qt crashes
        """
        self.closer.stop()
        self.model.model_stop()
        # Not "are you sure" about the changed circuit
        self.model._changed = False
        self.window.close()
        self.spin()
        self.window.deleteLater()
        self.spin()
        # Qt crashes at exit with data of its own on the clipboard
        QApplication.clipboard().clear()
        self.spin()

    # Qt helpers

    def spin(self, ms: int = 20) -> None:
        """Let Qt handle events for a while"""
        loop = QEventLoop()
        QTimer.singleShot(ms, loop.quit)
        loop.exec()

    def _close_dialogs(self) -> None:
        widget = QApplication.activeModalWidget()
        if widget is not None:
            widget.close()

    @property
    def scene(self) -> Any:
        """The circuit area scene"""
        return self.area.scene()

    def _view_pos(self, pos: tuple[float, float]) -> Any:
        scene_pos = QPointF(*pos)
        view_pos = self.area.mapFromScene(scene_pos)
        if not self.area.viewport().rect().contains(view_pos):
            self.area.centerOn(scene_pos)
            self.spin()
            view_pos = self.area.mapFromScene(scene_pos)
        return view_pos

    def _mouse(self, kind: QEvent.Type, pos: tuple[float, float], button: Qt.MouseButton) -> None:
        view_pos = self._view_pos(pos)
        buttons = button if kind == QEvent.Type.MouseButtonPress else Qt.MouseButton.NoButton
        if kind == QEvent.Type.MouseMove and self._held is not None:
            buttons = self._held
        event = QMouseEvent(
            kind,
            QPointF(view_pos),
            QPointF(self.area.viewport().mapToGlobal(view_pos)),
            button,
            buttons,
            Qt.KeyboardModifier.NoModifier,
        )
        QApplication.sendEvent(self.area.viewport(), event)

    _held: Qt.MouseButton | None = None

    def move(self, pos: tuple[float, float]) -> None:
        """Move the mouse"""
        self._mouse(QEvent.Type.MouseMove, pos, Qt.MouseButton.NoButton)
        self.spin(5)

    def press(self, pos: tuple[float, float]) -> None:
        """Press the left button"""
        self.move(pos)
        self._held = Qt.MouseButton.LeftButton
        self._mouse(QEvent.Type.MouseButtonPress, pos, Qt.MouseButton.LeftButton)

    def release(self, pos: tuple[float, float]) -> None:
        """Release the left button"""
        self._held = None
        self._mouse(QEvent.Type.MouseButtonRelease, pos, Qt.MouseButton.LeftButton)
        self.spin(10)

    def click(self, pos: tuple[float, float]) -> None:
        """A left click"""
        self.press(pos)
        self.release(pos)

    def drag(self, start: tuple[float, float], end: tuple[float, float]) -> None:
        """Press, move in steps and release"""
        self.press(start)
        for step in range(1, 5):
            self.move(
                (
                    start[0] + (end[0] - start[0]) * step / 4,
                    start[1] + (end[1] - start[1]) * step / 4,
                )
            )
        self.release(end)

    def context_menu(self, pos: tuple[float, float], text: str) -> dict[str, bool]:
        """Right-click and choose a menu item if it is enabled, return the items' states"""
        state: dict[str, bool] = {}

        def pick() -> None:
            menu = QApplication.activePopupWidget()
            if not isinstance(menu, QMenu):
                return
            actions = {action.text(): action for action in menu.actions() if action.text()}
            state.update({name: action.isEnabled() for name, action in actions.items()})
            if text in actions and actions[text].isEnabled():
                actions[text].trigger()
            menu.close()

        QTimer.singleShot(50, pick)
        view_pos = self._view_pos(pos)
        right = Qt.MouseButton.RightButton
        self._mouse(QEvent.Type.MouseButtonPress, pos, right)
        QApplication.sendEvent(
            self.area.viewport(),
            QContextMenuEvent(
                QContextMenuEvent.Reason.Mouse,
                view_pos,
                self.area.viewport().mapToGlobal(view_pos),
            ),
        )
        self._mouse(QEvent.Type.MouseButtonRelease, pos, right)
        self.spin(80)
        return state

    def snap(self, pos: tuple[float, float]) -> tuple[float, float]:
        """The scene position that a click at a position gets (the view has whole pixels)"""
        scene_pos = self.area.mapToScene(self._view_pos(pos))
        return scene_pos.x(), scene_pos.y()

    def top_item(self, pos: tuple[float, float]) -> QGraphicsItem | None:
        """The item that gets a click at a position (the view looks at a whole pixel)"""
        return self.area.itemAt(self._view_pos(pos))

    # The state of the GUI and the circuit

    def wire_items(self) -> dict[Wire, WireGraphicsItem]:
        """The wire items, by (output, input) port (in a fixed order, for the seed)"""
        items = [item for item in self.scene.items() if isinstance(item, WireGraphicsItem)]
        return {item.wire: item for item in sorted(items, key=lambda i: drawn_key(i.wire))}

    def component_objects(self) -> list[ComponentObject]:
        """The components in the GUI"""
        return self.model.objects.components.get_object_list()

    def connections(self) -> set[tuple[Port, Port]]:
        """The connections in the circuit, between top level components"""
        return {
            (src_port, dst_port)
            for component in self.model.objects.circuit.get_toplevel_components()
            for src_port in component.outports()
            for dst_port in src_port.wired_ports
        }

    def port_pos(self, port: Port) -> tuple[float, float]:
        """The center of a port in the scene"""
        item = self.model.objects.components.get_object(port.parent()).get_port_item(port)
        pos = item.portPos()
        return pos.x(), pos.y()

    def route(self, item: WireGraphicsItem) -> list[tuple[float, float]]:
        """The line from the output port to the input port of a wire, over its parents"""
        points = item.corner_points()
        branch = item._branch
        if branch is None:
            return points
        parent, corner = branch
        parent_route = self.route(parent)
        # The parent's own points are the last ones of its route
        start = len(parent_route) - len(parent.corner_points())
        return parent_route[: start + corner] + points

    def gui_lines(self) -> tuple[Lines, dict[Node, tuple[list[Port], list[Port]]]]:
        """
        The lines that the wire items make, connected through their ports and the corners
        where they start or end, and the output and input ports of each line
        """
        items = self.wire_items().values()
        nodes: list[tuple[Node, Node]] = []
        for item in items:
            start: Node = (
                ("port", item._src_port)
                if item._branch is None
                else ("wire", item._branch[0].wire)
            )
            end: Node = (
                ("port", item.dst_port) if item._join is None else ("wire", item._join[0].wire)
            )
            nodes.append((start, end))
        lines = Lines((item.wire, *pair) for item, pair in zip(items, nodes, strict=True))
        # The wires of a line connect its ports once, without a loop
        loops = Lines([])
        for item, (start, end) in zip(items, nodes, strict=True):
            node: Node = ("wire", item.wire)
            for other in (start, end):
                check(
                    not loops.same(node, other),
                    f"{drawn_key(item.wire)} closes a loop of its line",
                )
                loops._union(node, other)
        ports: dict[Node, tuple[list[Port], list[Port]]] = {}
        for start, end in nodes:
            for node in (start, end):
                port = node[1]
                if node[0] == "port" and isinstance(port, Port):
                    outputs, inputs = ports.setdefault(lines.find(node), ([], []))
                    group = outputs if port.is_output() else inputs
                    if port not in group:
                        group.append(port)
        return lines, ports

    def same_line(self, first: Node, second: Node) -> bool:
        """Are two ports or wires on the same line in the GUI"""
        return self.gui_lines()[0].same(first, second)

    def line_items(self, wire: Wire) -> set[Wire]:
        """The wires of the line of a wire in the GUI"""
        lines, _ = self.gui_lines()
        return {
            other for other in self.wire_items() if lines.same(("wire", other), ("wire", wire))
        }

    def attached(self, wires: set[Wire]) -> set[Wire]:
        """The wires that start or end on some wires, and those that start or end on them..."""
        model = self.model.objects.wires
        found = set(wires)
        added = True
        while added:
            added = False
            for wire in self.wire_items():
                anchors = [model.branch(wire), model.join(wire)]
                if wire not in found and any(a is not None and a[0] in found for a in anchors):
                    found.add(wire)
                    added = True
        return found - wires

    def snapshot(self) -> Any:
        """What undo must restore: the components, connections, wires' lines and paths"""
        gui = self.model.objects.components.get_gui_dict()
        components = {name: (pos.x, pos.y, pos.rotation, pos.flipped) for name, pos in gui.items()}
        connections = sorted(
            (port_key(src_port), port_key(dst_port)) for src_port, dst_port in self.connections()
        )
        routes = {
            drawn_key(wire): simplify(self.route(item)) for wire, item in self.wire_items().items()
        }
        # The paths too: a change can keep the line, like merging a step without length
        paths = self.model.objects.wires.to_dict()
        return components, connections, routes, paths

    def routes(self) -> dict[Wire, list[tuple[float, float]]]:
        """
        The line of each wire, from the output port to the input port. By wire, not by its
        name in the file: that changes when a wire to a shared input is added or deleted.
        """
        return {wire: simplify(self.route(item)) for wire, item in self.wire_items().items()}

    def grab(self) -> QImage:
        """The circuit area as it is painted now"""
        return self.area.viewport().grab().toImage()

    def painted(self, image: QImage, pos: tuple[float, float]) -> bool:
        """Is anything but the background painted at (or next to) a scene position"""
        view_pos = self.area.mapFromScene(QPointF(*pos))
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                x, y = view_pos.x() + dx, view_pos.y() + dy
                if 0 <= x < image.width() and 0 <= y < image.height():
                    color = image.pixelColor(x, y)
                    if (color.red(), color.green(), color.blue()) not in BACKGROUND:
                        return True
        return False

    def on_top(self, pos: tuple[float, float], item: QGraphicsItem) -> bool:
        """Is an item visible on top at a scene position, in the view"""
        view_pos = self.area.mapFromScene(QPointF(*pos))
        if not self.area.viewport().rect().adjusted(2, 2, -2, -2).contains(view_pos):
            return False
        return self.area.itemAt(view_pos) is item

    def check_painted(self) -> None:
        """Every segment with a length is painted, where nothing covers it"""
        image = self.grab()
        for item in self.wire_items().values():
            for part in item.part_items:
                start, end = part._start, part._end
                if start == end:
                    continue
                mid = ((start.x() + end.x()) / 2, (start.y() + end.y()) / 2)
                if self.on_top(mid, part):
                    check(
                        self.painted(image, mid),
                        f"{drawn_key(item.wire)} segment {part.segment} is not painted at {mid}",
                    )

    def check_new_wire_painted(self, pos: tuple[float, float]) -> None:
        """The wire being drawn goes to the mouse, and is painted"""
        (item,) = [i for i in self.scene.items() if isinstance(i, NewWireGraphicsItem)]
        # Painted first, as the user sees it
        image = self.grab()
        path = item.path()
        check(path.elementCount() >= 2, "the wire being drawn has no path")
        x, y = self.snap(pos)
        last = path.elementAt(path.elementCount() - 1)
        check(
            (round(last.x), round(last.y)) == (round(x), round(y)),
            f"the wire being drawn ends at {(last.x, last.y)}, not at the mouse {(x, y)}",
        )
        before = path.elementAt(path.elementCount() - 2)
        mid = ((before.x + last.x) / 2, (before.y + last.y) / 2)
        if abs(before.x - last.x) + abs(before.y - last.y) > 8 and self.on_top(mid, item):
            check(self.painted(image, mid), f"the wire being drawn is not painted at {mid}")

    def check_invariants(self) -> None:
        """The GUI matches the circuit, and the wires are drawn where they belong"""
        circuit = self.model.objects.circuit
        components = self.model.objects.components
        toplevel = set(circuit.get_toplevel_components())
        objects = set(components.get_dict())
        check(toplevel == objects, f"circuit components {toplevel} != GUI {objects}")
        scene_objects = {i for i in self.scene.items() if isinstance(i, ComponentObject)}
        check(
            {obj.component for obj in scene_objects} == objects,
            "the scene doesn't show the model's components",
        )
        # A click selects the piece of a line as the model has it now
        check(
            self.scene._runs == self.model.objects.wires.runs(),
            "the scene's pieces of the lines are not the model's",
        )
        for component in toplevel:
            for port in component.ports:
                drivers = port.get_drivers() if not port.is_output() else []
                check(
                    all(driver.parent() in toplevel for driver in drivers),
                    f"{port_key(port)} is driven by a deleted component",
                )
                check(
                    len(set(drivers)) == len(drivers),
                    f"{port_key(port)} has the same driver twice",
                )
                for wired in port.wired_ports if port.is_output() else []:
                    check(wired.parent() in toplevel, f"{port_key(port)} drives a deleted port")
        items = self.wire_items()
        wire_items = [i for i in self.scene.items() if isinstance(i, WireGraphicsItem)]
        check(len(wire_items) == len(items), "two wire items for the same wire")
        gui = set(items)
        connections = self.connections()
        wires = self.model.objects.wires
        drawn = set(wires.drawn())
        check(
            gui == drawn,
            "GUI wires != drawn wires: "
            + str(sorted(f"{port_key(s)}->{port_key(d)}" for s, d in gui ^ drawn)),
        )
        implied = {wire for wire in connections if wires.is_implied(wire)}
        check(
            connections <= drawn | implied,
            "connections that are neither drawn nor implied: "
            + str(sorted(map(wire_key, connections - drawn - implied))),
        )
        self.check_lines(connections)
        self.check_dots()
        for part in [i for i in self.scene.items() if isinstance(i, WirePartGraphicsItem)]:
            check(part.parentItem() in wire_items, "a wire segment without its wire")
        check(
            set(wires.to_dict())
            == {wire_key(wire) for wire in implied} | {drawn_key(wire) for wire in drawn},
            "the saved wires are not the drawn and the implied wires",
        )
        for wire, item in items.items():
            name = drawn_key(wire)
            points = item.corner_points()
            check(len(item._path) % 2 == 1, f"{name}: invalid path {item._path}")
            check(points == wires.corner_points(wire), f"{name}: GUI and model differ")
            joint = wires.join(wire)
            if joint is None:
                check(points[-1] == self.port_pos(wire[1]), f"{name}: doesn't end at its port")
                check(item._join is None, f"{name}: joins a line in the GUI only")
            else:
                self.check_joined(wire, item, items)
            branch = wires.branch(wire)
            if branch is None:
                check(item._branch is None, f"{name}: a branch in the GUI only")
                check(
                    points[0] == self.port_pos(item._src_port),
                    f"{name}: doesn't start at its output port",
                )
            else:
                parent, corner = branch
                check(
                    item._branch is not None and item._branch[0].wire == parent,
                    f"{name}: starts on another wire in the GUI",
                )
                check(
                    parent[0] is item._src_port,
                    f"{name}: starts on a wire from another output",
                )
                parent_points = items[parent].corner_points()
                check(
                    1 <= corner <= len(parent_points) - 2,
                    f"{name}: starts at corner {corner}, not an inner corner",
                )
                check(
                    points[0] == parent_points[corner],
                    f"{name}: doesn't start at its corner",
                )
                check(
                    wire not in wires.route(parent),
                    f"{name}: starts on itself",
                )
        selected = self.scene._selected_wires
        check(selected <= set(items), "a deleted wire is selected")
        self.check_painted()

    @staticmethod
    def ways(point: tuple[float, float], items: list[WireGraphicsItem]) -> set[tuple[int, int]]:
        """The ways that the segments of some wires go from a point"""
        found = set()
        for item in items:
            for (x1, y1), (x2, y2) in pairwise(item.corner_points()):
                if (x1, y1) == (x2, y2):
                    continue
                on_x = y1 == y2 == point[1] and min(x1, x2) <= point[0] <= max(x1, x2)
                on_y = x1 == x2 == point[0] and min(y1, y2) <= point[1] <= max(y1, y2)
                if not (on_x or on_y):
                    continue
                for x, y in ((x1, y1), (x2, y2)):
                    if (x, y) != point:
                        found.add(
                            ((x > point[0]) - (x < point[0]), (y > point[1]) - (y < point[1]))
                        )
        return found

    def check_dots(self) -> None:
        """A dot where the wires of a line go three or more ways, and nowhere else"""
        lines, _ = self.gui_lines()
        items = list(self.wire_items().values())
        groups: dict[Node, list[WireGraphicsItem]] = {}
        for item in items:
            groups.setdefault(lines.find(("wire", item.wire)), []).append(item)
        for line_items in groups.values():
            drawn = {
                point for item in line_items for part in item.part_items for point, _ in part._dots
            }
            ends = {point for item in line_items for point in item.corner_points()}
            expected = {point for point in ends if len(self.ways(point, line_items)) >= 3}
            check(
                drawn == expected,
                f"dots at {sorted(drawn - expected)} where the line doesn't meet, "
                f"none at {sorted(expected - drawn)} where it does",
            )

    def check_lines(self, connections: set[Wire]) -> None:
        """
        Each output port of a line drives each input port of it, and a connection is
        between ports of the same line
        """
        lines, ports = self.gui_lines()
        for src_port, dst_port in connections:
            check(
                lines.same(("port", src_port), ("port", dst_port)),
                f"{port_key(src_port)} drives {port_key(dst_port)}, not on its line",
            )
        for outputs, inputs in ports.values():
            for src_port in outputs:
                for dst_port in inputs:
                    check(
                        (src_port, dst_port) in connections,
                        f"{port_key(src_port)} doesn't drive {port_key(dst_port)} of its line",
                    )

    def check_joined(
        self, wire: Wire, item: WireGraphicsItem, items: dict[Wire, WireGraphicsItem]
    ) -> None:
        """A joined wire ends at a corner of another wire"""
        wires = self.model.objects.wires
        name = drawn_key(wire)
        joint = wires.join(wire)
        assert joint is not None
        host, corner = joint
        check(host in items, f"{name}: joins a deleted wire")
        check(host != wire, f"{name}: ends on itself")
        check(
            item._join is not None and item._join[0].wire == host,
            f"{name}: joins another line in the GUI",
        )
        host_points = items[host].corner_points()
        check(1 <= corner <= len(host_points) - 2, f"{name}: ends at corner {corner} of its line")
        check(
            item.corner_points()[-1] == host_points[corner],
            f"{name}: doesn't end at its corner of the line",
        )
        check(
            self.same_line(("port", wire[1]), ("wire", wire)),
            f"{name}: is known by {port_key(wire[1])}, not on its line",
        )

    # Choices

    def free_inputs(self, width: int | None = None, wire: Wire | None = None) -> list[Port]:
        """Input ports without a driver (not on the line of a wire)"""
        return [
            port
            for obj in self.component_objects()
            for port in obj.component.inports()
            if not port.has_driver()
            and (width is None or port.width == width)
            and (wire is None or not self.same_line(("port", port), ("wire", wire)))
        ]

    def outputs(self) -> list[Port]:
        """All output ports"""
        return [port for obj in self.component_objects() for port in obj.component.outports()]

    def inputs(self) -> list[Port]:
        """All input ports"""
        return [port for obj in self.component_objects() for port in obj.component.inports()]

    def port_click_pos(self, port: Port) -> tuple[float, float]:
        """Where a click hits a port, Skip if another item is on top of it"""
        pos = self.snap(self.port_pos(port))
        top = self.top_item(pos)
        if not isinstance(top, PortGraphicsItem) or top.port is not port:
            raise Skip("port covered")
        return pos

    def free_pos(self) -> tuple[float, float]:
        """
        A position in the circuit area that is not on a port, or on a wire (where a wire
        drawn from an input port ends)
        """
        radius = WirePartGraphicsItem.CORNER_RADIUS + 2
        for _ in range(20):
            pos = (
                round(self.rng.uniform(0, GRID_COLUMNS * CELL_WIDTH)),
                round(self.rng.uniform(0, GRID_ROWS * CELL_HEIGHT)),
            )
            items = self.scene.items(QPointF(*pos))
            if not any(
                isinstance(item, PortGraphicsItem)
                or (
                    isinstance(item, WirePartGraphicsItem)
                    and item.distance(QPointF(*pos)) <= radius
                )
                for item in items
            ):
                return pos
        raise Skip("no free position")

    def retry(self, choose: Callable[[], Any], attempts: int = 10) -> Any:
        """A random choice that is tried again when it hits the wrong item"""
        for _ in range(attempts - 1):
            try:
                return choose()
            except Skip:
                pass
        return choose()

    def segment_pos(
        self, wanted: Callable[[Wire], bool] | None = None
    ) -> tuple[WirePartGraphicsItem, tuple[float, float]]:
        """
        A position on a random wire segment (of the wires that are 'wanted'), and the
        segment that a click there hits
        """
        return self.retry(lambda: self._segment_pos(wanted))

    def _segment_pos(
        self, wanted: Callable[[Wire], bool] | None = None
    ) -> tuple[WirePartGraphicsItem, tuple[float, float]]:
        items = [
            item for wire, item in self.wire_items().items() if wanted is None or wanted(wire)
        ]
        if not items:
            raise Skip("no wires")
        item = self.rng.choice(items)
        points = item.corner_points()
        segment = self.rng.randrange(len(points) - 1)
        (x1, y1), (x2, y2) = points[segment : segment + 2]
        if (x1, y1) == (x2, y2):
            raise Skip("segment without length")
        fraction = self.rng.uniform(0.15, 0.85)
        pos = self.snap((x1 + (x2 - x1) * fraction, y1 + (y2 - y1) * fraction))
        top = self.top_item(pos)
        if not isinstance(top, WirePartGraphicsItem):
            raise Skip("segment covered")
        # The segment on top must be the one at the point, not one beside it
        if top.distance(QPointF(*pos)) > 1:
            raise Skip("another segment on top")
        # Not at a corner (where a wire ends) or a dot or a joint (that drags)
        at_corner = top._parent.corner_at(QPointF(*pos), WirePartGraphicsItem.CORNER_RADIUS)
        at_dot = top._handle_at(QPointF(*pos)) is not None or self.scene._wire_point_at(
            QPointF(*pos)
        )
        if at_corner is not None or at_dot:
            raise Skip("on a corner or a dot")
        return top, pos

    def clear_selection(self) -> None:
        """Select nothing, also no point"""
        self.scene._clear_point()
        self.scene.clearSelection()
        self.spin(5)

    # Actions, each returns a description for the log

    def add_component(self) -> str:
        if len(self.component_objects()) >= MAX_COMPONENTS or not self.free_cells:
            raise Skip("full")
        name, settings = self.rng.choice(COMPONENTS)
        used = set()
        for obj in self.component_objects():
            center = obj.rect().translated(obj.pos()).center()
            used.add((int(center.x() // CELL_WIDTH), int(center.y() // CELL_HEIGHT)))
        cells = [cell for cell in self.free_cells if cell not in used]
        if not cells:
            raise Skip("no free cell")
        col, row = self.rng.choice(cells)
        pos = QPointF(col * CELL_WIDTH + 40, row * CELL_HEIGHT + 40)
        component_object = self.model.objects.components.add_object_by_name(name, pos, settings)
        check(component_object is not None, f"could not add {name}")
        assert component_object is not None
        self.area._scene.add_scene_component(component_object, True)
        self.spin()
        return f"add {name} {settings} at {(col, row)}"

    def _draw(
        self,
        start: Callable[[], None],
        end: Port | tuple[float, float],
        corners: int,
        expect_ok: bool,
    ) -> tuple[list[tuple[float, float]], bool]:
        """Draw a wire: start it, click corners, and click the end port (or position)"""
        end_pos = self.port_click_pos(end) if isinstance(end, Port) else end
        clicks = [self.free_pos() for _ in range(corners)]
        before = len(self.errors)
        start()
        check(self.model.objects.new_wire.ongoing(), "the wire didn't start")
        for pos in clicks:
            self.click(pos)
        if clicks and self.rng.random() < 0.3:
            # Correct the last click with Backspace
            QTest.keyClick(self.window, Qt.Key.Key_Backspace)
            clicks.pop()
        # On the way to the end: the wire follows the mouse
        mouse = self.free_pos()
        self.move(mouse)
        self.check_new_wire_painted(mouse)
        self.click(end_pos)
        self.spin()
        check(not self.model.objects.new_wire.ongoing(), "the wire wasn't finished")
        failed = len(self.errors) > before
        check(
            failed != expect_ok,
            f"the connection {'failed' if failed else 'worked'}: {self.errors[before:]}",
        )
        return clicks, not failed

    def check_drawn_shape(
        self, wire: Wire, clicks: list[tuple[float, float]], from_source: bool
    ) -> None:
        """
        A finished wire has the shape it was drawn with: across to each click and up or
        down to it, and then to the other end, with its last bend just before that end
        """
        wires = self.model.objects.wires
        points = wires.corner_points(wire)
        if wires._turned_ends(wire) is not None:
            # To a port of a rotated component, see check_turned_ends()
            self.check_turned_ends(wire)
            return
        if not clicks and not is_forwards(points[0], points[-1]) and wires.branch(wire) is None:
            # Backwards without clicks: the automatic route around the component
            return
        branch = wires.branch(wire)
        if branch is not None:
            # Drawn on along the wire it starts on, at the same height: a step down instead
            joint, port = points[0], points[-1]
            near = (clicks[0] if from_source else clicks[-1]) if clicks else port
            way = "right" if near[0] > joint[0] else "left"
            if near[1] == joint[1] and way in wires.taken_directions(*branch):
                return
        if not from_source:
            points = points[::-1]
        start, end = points[0], points[-1]
        if branch is not None and from_source:
            taken = wires.taken_directions(*branch)
            if exits_vertically(taken, start, clicks[0] if clicks else end):
                # Up or down from the corner first, then exactly like it was drawn
                drawn = drawing_points(start, [*clicks, end], vertical_first=True)
                check(
                    simplify(points) == simplify(drawn),
                    f"the wire doesn't keep its drawn shape: {points} != {drawn}",
                )
                return
        drawn = drawing_points(start, [*clicks, end])
        if from_source:
            step = -X_OFFSET
            if branch is not None and not clicks and end[0] + step == start[0]:
                # The port is just beside the corner: up or down halfway to it
                step = math.floor((start[0] + end[0]) / 2) - end[0]
        elif branch is not None:
            # A wire reaches another wire without the step that a port needs, unless it
            # would reach it along the other wire
            taken = wires.taken_directions(*branch)
            step = arrival_offset(taken, end, drawn[-3])
        else:
            step = X_OFFSET
        expected = [*drawn[:-2], (end[0] + step, drawn[-3][1]), (end[0] + step, end[1]), end]
        check(points == expected, f"the wire doesn't keep its drawn shape: {points} != {expected}")

    def check_turned_ends(self, wire: Wire) -> None:
        """
        A wire to a port of a rotated component leaves and reaches its ports along their
        directions: across from a port that faces across, up or down from one that faces
        up or down
        """
        wires = self.model.objects.wires
        points = simplify(wires.corner_points(wire))
        directions = wires._turned_ends(wire)
        assert directions is not None
        for direction, (port_point, next_point) in zip(
            directions, ((points[0], points[1]), (points[-1], points[-2])), strict=True
        ):
            if direction is None or port_point == next_point:
                continue
            vertical = port_point[0] == next_point[0]
            check(
                vertical == faces_vertically(direction),
                f"{drawn_key(wire)}: leaves a port that faces {direction} the other way",
            )

    def check_across(self, wire: Wire) -> None:
        """A new branch leaves (or reaches) a joint across the wire, not along it"""
        wires = self.model.objects.wires
        branch = wires.branch(wire)
        check(branch is not None, f"{drawn_key(wire)} is not a branch")
        assert branch is not None
        taken = wires.taken_directions(*branch)
        if taken not in ({"left", "right"}, {"up", "down"}):
            return  # a corner: the user's clicks may lead along the wire
        start, *rest = wires.corner_points(wire)
        other = next(point for point in rest if point != start)
        if other[0] != start[0]:
            way = "right" if other[0] > start[0] else "left"
        else:
            way = "down" if other[1] > start[1] else "up"
        check(way not in taken, f"{drawn_key(wire)} runs {way} along the wire from the joint")

    def connect_ports(self) -> str:
        outputs = self.outputs()
        if not outputs:
            raise Skip("no outputs")
        src_port = self.rng.choice(outputs)
        inputs = self.free_inputs(src_port.width)
        if not inputs:
            raise Skip("no free input")
        dst_port = self.rng.choice(inputs)
        from_output = self.rng.random() < 0.6
        start_port, end_port = (src_port, dst_port) if from_output else (dst_port, src_port)
        start_pos = self.port_click_pos(start_port)
        clicks, _ = self._draw(
            lambda: self.click(start_pos), end_port, self.rng.randint(0, 3), expect_ok=True
        )
        check((src_port, dst_port) in self.connections(), "the wire is not in the circuit")
        self.check_drawn_shape((src_port, dst_port), clicks, from_output)
        check(
            self.model.objects.wires.branch((src_port, dst_port)) is None,
            "a wire from a port starts on a wire",
        )
        return f"wire {port_key(start_port)} -> {port_key(end_port)} corners {clicks}"

    def connect_shared(self) -> str:
        """An output to an input that other outputs drive: a wire of its own"""
        outputs = self.outputs()
        if not outputs:
            raise Skip("no outputs")
        src_port = self.rng.choice(outputs)
        inputs = [
            port
            for obj in self.component_objects()
            for port in obj.component.inports()
            if port.width == src_port.width
            and port.has_driver()
            and not self.same_line(("port", src_port), ("port", port))
        ]
        if not inputs:
            raise Skip("no shared input")
        dst_port = self.rng.choice(inputs)
        drivers = dst_port.get_drivers()
        before = self.routes()
        from_output = self.rng.random() < 0.6
        start_port, end_port = (src_port, dst_port) if from_output else (dst_port, src_port)
        start_pos = self.port_click_pos(start_port)
        clicks, _ = self._draw(
            lambda: self.click(start_pos), end_port, self.rng.randint(0, 3), expect_ok=True
        )
        check(
            dst_port.get_drivers()[: len(drivers) + 1] == [*drivers, src_port],
            f"{port_key(dst_port)} is driven by {list(map(port_key, dst_port.get_drivers()))}",
        )
        wire = (src_port, dst_port)
        check(self.model.objects.wires.branch(wire) is None, "a wire from a port is a branch")
        self.check_drawn_shape(wire, clicks, from_output)
        after = self.routes()
        changed = [drawn_key(key) for key in before if before[key] != after.get(key)]
        check(not changed, f"other wires changed: {changed}")
        return f"shared wire {port_key(start_port)} -> {port_key(end_port)} corners {clicks}"

    def connect_join(self) -> str:
        """
        A wire from an output to the line of another output: it drives all the line's
        inputs then. On a line that can't be joined, the click is a corner.
        """
        outputs = self.outputs()
        if not outputs:
            raise Skip("no outputs")
        src_port = self.rng.choice(outputs)
        wires = self.model.objects.wires

        def can_join(line: Wire) -> bool:
            return src_port.width == line[0].width and not self.same_line(
                ("port", src_port), ("wire", line)
            )

        # Mostly a line that can be joined, sometimes any line (a corner then)
        if self.rng.random() < 0.8:
            part, pos = self.segment_pos(can_join)
        else:
            part, pos = self.segment_pos()
        line = part.wire_item.wire
        expect_ok = can_join(line)
        start_pos = self.port_click_pos(src_port)
        self.clear_selection()
        before = self.routes()
        connections = self.connections()
        targets: list[Any] = []
        if not expect_ok:
            return self._corner_on_line(start_pos, drawn_key(line), pos, connections)

        def start() -> None:
            self.click(start_pos)
            target = self.scene.wire_end_at(QPointF(*pos))
            # At the edge of an item, the view and the scene may see different items
            if target is None or target[0] != line:
                raise Skip("another item at the edge")
            targets.append(target)

        self._draw(start, pos, self.rng.randint(0, 2), expect_ok=True)
        after = self.routes()
        changed = [drawn_key(key) for key in before if before[key] != after.get(key)]
        check(not changed, f"other wires changed: {changed}")
        check(connections <= self.connections(), "a connection is gone")
        _, number, point = targets[0]
        if src_port.is_input():
            # An inout port is an input too: like from an input, the wire is a branch of
            # the line, from its output port. The inout port drives the line all the same.
            return self._check_inout_branch(src_port, line, number, point, pos)
        wire = (src_port, line[1])
        check(wire in self.wire_items(), f"no wire {drawn_key(wire)}")
        joint = wires.join(wire)
        check(joint is not None and joint[0] == line, f"joins {joint}, not {drawn_key(line)}")
        assert joint is not None
        end = wires.corner_points(wire)[-1]
        if point is None:
            check(joint[1] == number, f"ends at corner {joint[1]}, not {number}")
        else:
            check(
                abs(end[0] - pos[0]) <= 1 and abs(end[1] - pos[1]) <= 1,
                f"ends at {end}, not {pos}",
            )
        return f"join {port_key(src_port)} -> {drawn_key(line)} at {end}"

    def _check_inout_branch(
        self,
        port: Port,
        line: Wire,
        number: int,
        point: tuple[float, float] | None,
        pos: tuple[float, float],
    ) -> str:
        """A wire drawn from an inout port to a line: a branch of it, to the port"""
        wires = self.model.objects.wires
        wire = (line[0], port)
        check(wire in self.wire_items(), f"no wire {drawn_key(wire)}")
        branch = wires.branch(wire)
        check(branch is not None and branch[0] == line, f"starts on {branch}, not the line")
        assert branch is not None
        start = wires.corner_points(wire)[0]
        if point is None:
            check(branch[1] == number, f"starts at corner {branch[1]}, not {number}")
        else:
            check(
                abs(start[0] - pos[0]) <= 1 and abs(start[1] - pos[1]) <= 1,
                f"starts at {start}, not {pos}",
            )
        inputs = [dst for dst in wires.line(("port", port)).inputs if dst is not port]
        check(
            all(dst in port.wired_ports for dst in inputs),
            "the inout port doesn't drive the line",
        )
        return f"join inout {port_key(port)} -> {drawn_key(line)} at {start}"

    def _corner_on_line(
        self,
        start_pos: tuple[float, float],
        name: str,
        pos: tuple[float, float],
        connections: set[Wire],
    ) -> str:
        """A click on a line that the wire being drawn can't end on: a corner"""
        items = self.scene.items(QPointF(*pos))
        if any(isinstance(item, PortGraphicsItem) for item in items):
            raise Skip("a port at the line")
        self.click(start_pos)
        new_wire = self.model.objects.new_wire
        check(new_wire.ongoing(), "the wire didn't start")
        if self.scene.wire_end_at(QPointF(*pos)) is not None:
            # Another line there, that can be joined
            QTest.keyClick(self.window, Qt.Key.Key_Escape)
            raise Skip("a line that can be joined at the same place")
        before = len(self.errors)
        self.click(pos)
        self.spin()
        check(len(self.errors) == before, f"an error: {self.errors[before:]}")
        check(new_wire.ongoing(), "a click on a line that can't be joined ended the wire")
        clicks = new_wire.clicks()
        check(
            bool(clicks) and abs(clicks[-1][0] - pos[0]) <= 1 and abs(clicks[-1][1] - pos[1]) <= 1,
            f"the corners are {clicks}, not ending at {pos}",
        )
        QTest.keyClick(self.window, Qt.Key.Key_Escape)
        self.spin()
        check(self.connections() == connections, "a line that can't be shared was joined")
        return f"corner on {name}, that the wire can't end on"

    def _corner_pos(self) -> tuple[WirePartGraphicsItem, tuple[float, float], int]:
        """A position on a random corner, the segment that a click there hits, its corner"""
        items = list(self.wire_items().values())
        if not items:
            raise Skip("no wires")
        # Half of the time a joint, a corner in a straight line, if there is one
        joints = [
            (item, corner)
            for item in items
            for corner in range(1, len(item.corner_points()) - 1)
            if corner_directions(item.corner_points(), corner)
            in ({"left", "right"}, {"up", "down"})
        ]
        if joints and self.rng.random() < 0.5:
            item, corner = self.rng.choice(joints)
            points = item.corner_points()
        else:
            item = self.rng.choice(items)
            points = item.corner_points()
            corner = self.rng.randrange(1, len(points) - 1)
        pos = self.snap(points[corner])
        top = self.top_item(pos)
        if not isinstance(top, WirePartGraphicsItem):
            raise Skip("corner covered")
        hit = top._parent.corner_at(QPointF(*pos), WirePartGraphicsItem.CORNER_RADIUS)
        # A dot of a selected wire is dragged, also close to a corner
        if hit is None or top._handle_at(QPointF(*pos)) is not None:
            raise Skip("another wire's segment or a dot at the corner")
        return top, pos, hit

    def start_wire_at(self, pos: tuple[float, float]) -> None:
        """Start a new wire on a wire, from its context menu"""
        state = self.context_menu(pos, "Start wire here")
        check(state.get("Start wire here", False), f"no Start wire here in {state}")
        check(self.model.objects.new_wire.ongoing(), "the wire didn't start")

    def connect_from_corner(self) -> str:
        top, pos, hit = self.retry(self._corner_pos)
        anchor = (top._parent.wire, hit)
        corner_point = top._parent.corner_points()[hit]
        src_port = top._parent._src_port
        inputs = self.free_inputs(src_port.width, anchor[0])
        if not inputs:
            raise Skip("no free input")
        dst_port = self.rng.choice(inputs)
        before = self.routes()
        clicks, _ = self._draw(
            lambda: self.start_wire_at(pos), dst_port, self.rng.randint(0, 2), expect_ok=True
        )
        wires = self.model.objects.wires
        wire = (src_port, dst_port)
        check(wire in self.wire_items(), "the branch is not drawn")
        self.check_drawn_shape(wire, clicks, from_source=True)
        check(
            wires.branch(wire) == anchor,
            f"the branch starts at {wires.branch(wire)}, not {anchor}",
        )
        check(
            wires.corner_points(wire)[0] == corner_point,
            "the branch doesn't start at the clicked corner",
        )
        self.check_across(wire)
        after = self.routes()
        changed = [drawn_key(key) for key in before if before[key] != after.get(key)]
        check(not changed, f"other wires changed: {changed}")
        return f"branch from {drawn_key(anchor[0])} corner {hit} -> {port_key(dst_port)}"

    def connect_join_from_line(self) -> str:
        """
        A wire drawn from a corner of a line to an output port: the output joins the line,
        and drives all its inputs
        """
        top, pos, hit = self.retry(self._corner_pos)
        line = top._parent.wire
        wires = self.model.objects.wires
        outputs = [
            port
            for port in self.outputs()
            if port.width == line[0].width and not self.same_line(("port", port), ("wire", line))
        ]
        if not outputs:
            raise Skip("no output that can join")
        src_port = self.rng.choice(outputs)
        corner_point = top._parent.corner_points()[hit]
        before = self.routes()
        connections = self.connections()
        clicks, _ = self._draw(
            lambda: self.start_wire_at(pos), src_port, self.rng.randint(0, 2), expect_ok=True
        )
        after = self.routes()
        changed = [drawn_key(key) for key in before if before[key] != after.get(key)]
        check(not changed, f"other wires changed: {changed}")
        wire = (src_port, line[1])
        check(wire in self.wire_items(), f"no wire {drawn_key(wire)}")
        check(connections <= self.connections(), "a connection is gone")
        check(wires.join(wire) == (line, hit), f"joins {wires.join(wire)}")
        check(
            wires.corner_points(wire)[-1] == corner_point,
            "the wire doesn't end at the clicked corner",
        )
        points = wires.corner_points(wire)
        check(
            all(
                any(abs(x - cx) <= 1 and abs(y - cy) <= 1 for x, y in points) for cx, cy in clicks
            ),
            f"the wire {points} doesn't run through the clicks {clicks}",
        )
        return f"join {port_key(src_port)} from {drawn_key(line)} corner {hit} corners {clicks}"

    def connect_lines(self) -> str:
        """A wire from a corner of a wire to a wire of another line: the lines become one"""
        # Before choosing: a selected wire is on top of the others
        self.clear_selection()
        top, pos, hit = self.retry(self._corner_pos)
        start = (top._parent.wire, hit)
        width = start[0][0].width

        def other_line(wire: Wire) -> bool:
            return wire[0].width == width and not self.same_line(
                ("wire", wire), ("wire", start[0])
            )

        part, end_pos = self.segment_pos(other_line)
        line = part.wire_item.wire
        before = self.routes()
        connections = self.connections()
        targets: list[Any] = []

        def start_wire() -> None:
            self.start_wire_at(pos)
            target = self.scene.wire_end_at(QPointF(*end_pos))
            # At the edge of an item, the view and the scene may see different items
            if target is None or target[0] != line:
                raise Skip("another item at the edge")
            targets.append(target)

        clicks, _ = self._draw(start_wire, end_pos, self.rng.randint(0, 2), expect_ok=True)
        after = self.routes()
        changed = [drawn_key(key) for key in before if before[key] != after.get(key)]
        check(not changed, f"other wires changed: {changed}")
        wires = self.model.objects.wires
        wire = (start[0][0], line[1])
        check(wire in self.wire_items(), f"no wire {drawn_key(wire)}")
        check(connections <= self.connections(), "a connection is gone")
        check(wires.branch(wire) == start, f"starts at {wires.branch(wire)}, not {start}")
        joint = wires.join(wire)
        check(joint is not None and joint[0] == line, f"ends on {joint}, not {drawn_key(line)}")
        assert joint is not None
        points = wires.corner_points(wire)
        _, number, point = targets[0]
        if point is None:
            check(joint[1] == number, f"ends at corner {joint[1]}, not {number}")
        else:
            check(
                abs(points[-1][0] - end_pos[0]) <= 1 and abs(points[-1][1] - end_pos[1]) <= 1,
                f"ends at {points[-1]}, not {end_pos}",
            )
        check(
            all(
                any(abs(x - cx) <= 1 and abs(y - cy) <= 1 for x, y in points) for cx, cy in clicks
            ),
            f"the wire {points} doesn't run through the clicks {clicks}",
        )
        return f"wire from {drawn_key(start[0])} corner {hit} to {drawn_key(line)} at {points[-1]}"

    def connect_to_corner(self) -> str:
        """A wire drawn from an input port to a corner of a wire, also of another width"""
        top, pos, hit = self.retry(self._corner_pos)
        anchor = (top.wire_item.wire, hit)
        corner_point = top.wire_item.corner_points()[hit]
        src_port = top.wire_item._src_port
        same_width = self.rng.random() < 0.85
        inputs = [
            p
            for p in self.free_inputs(wire=anchor[0])
            if (p.width == src_port.width) == same_width
        ]
        if not inputs:
            raise Skip("no free input")
        dst_port = self.rng.choice(inputs)
        start_pos = self.port_click_pos(dst_port)
        if not same_width:
            # Not on a wire of another width, the click is a corner of the wire
            self.clear_selection()
            name = f"{drawn_key(anchor[0])} corner {hit} of another width"
            return self._corner_on_line(start_pos, name, pos, self.connections())
        before = self.routes()
        clicks, _ = self._draw(
            lambda: self.click(start_pos), pos, self.rng.randint(0, 2), expect_ok=True
        )
        after = self.routes()
        changed = [drawn_key(key) for key in before if before[key] != after.get(key)]
        check(not changed, f"other wires changed: {changed}")
        wires = self.model.objects.wires
        wire = (src_port, dst_port)
        check(wire in self.wire_items(), "the branch is not drawn")
        check(
            wires.branch(wire) == anchor,
            f"the branch starts at {wires.branch(wire)}, not {anchor}",
        )
        check(
            wires.corner_points(wire)[0] == corner_point,
            "the branch doesn't start at the clicked corner",
        )
        self.check_drawn_shape(wire, clicks, from_source=False)
        self.check_across(wire)
        return f"branch {port_key(dst_port)} -> {drawn_key(anchor[0])} corner {hit}"

    def connect_to_segment(self) -> str:
        """A wire drawn from an input port to a straight part of a wire, at a new joint"""
        part, pos = self.retry(self.segment_pos)
        src_port = part.wire_item._src_port
        inputs = self.free_inputs(src_port.width, part.wire_item.wire)
        if not inputs:
            raise Skip("no free input")
        dst_port = self.rng.choice(inputs)
        start_pos = self.port_click_pos(dst_port)
        self.clear_selection()
        before = self.routes()
        targets: list[Any] = []

        def start() -> None:
            self.click(start_pos)
            target = self.scene.wire_end_at(QPointF(*pos))
            # At the edge of an item, the view and the scene may see different items
            if target is None or target[0] != part.wire_item.wire:
                raise Skip("another item at the edge")
            targets.append(target)

        drawn, _ = self._draw(start, pos, self.rng.randint(0, 2), expect_ok=True)
        # The wire on top, at its corner close by or on the segment
        wire, number, point = targets[0]
        wires = self.model.objects.wires
        check((src_port, dst_port) in self.wire_items(), "the branch is not drawn")
        branch = wires.branch((src_port, dst_port))
        start_point = wires.corner_points((src_port, dst_port))[0]
        if point is None:
            check(branch == (wire, number), f"the branch starts at {branch}, not corner {number}")
        else:
            check(branch is not None and branch[0] == wire, f"the branch starts on {branch}")
            check(
                abs(start_point[0] - pos[0]) <= 1 and abs(start_point[1] - pos[1]) <= 1,
                f"the branch starts at {start_point}, not {pos}",
            )
        after = self.routes()
        changed = [drawn_key(key) for key in before if before[key] != after.get(key)]
        check(not changed, f"other wires changed: {changed}")
        self.check_drawn_shape((src_port, dst_port), drawn, from_source=False)
        self.check_across((src_port, dst_port))
        return f"branch {port_key(dst_port)} -> {drawn_key(wire)} at {start_point}"

    def connect_invalid(self) -> str:
        """A connection that must fail: to a driven input, another width, or the same port"""
        outputs = self.outputs()
        if not outputs:
            raise Skip("no outputs")
        src_port = self.rng.choice(outputs)
        kind = self.rng.choice(["driven", "width", "itself"])
        if kind == "driven":
            # An input that the output drives already
            candidates = sorted((d for s, d in self.connections() if s is src_port), key=port_key)
        elif kind == "width":
            candidates = [p for p in self.free_inputs() if p.width != src_port.width]
        else:
            candidates = [src_port]
        if not candidates:
            raise Skip("no candidate")
        end_port = self.rng.choice(candidates)
        start_pos = self.port_click_pos(src_port)
        self._draw(lambda: self.click(start_pos), end_port, 0, expect_ok=False)
        return f"invalid ({kind}) {port_key(src_port)} -> {port_key(end_port)}"

    def connect_same_kind(self) -> str:
        """A wire between two output ports, or two input ports: their lines become one"""
        ports = self.outputs() if self.rng.random() < 0.5 else self.inputs()
        if len(ports) < 2:
            raise Skip("too few ports")
        start_port = self.rng.choice(ports)
        others = [
            port
            for port in ports
            if port is not start_port
            and port.width == start_port.width
            and not self.same_line(("port", start_port), ("port", port))
        ]
        if not others:
            raise Skip("no port on another line")
        end_port = self.rng.choice(others)
        start_pos = self.port_click_pos(start_port)
        before = self.routes()
        connections = self.connections()
        clicks, _ = self._draw(
            lambda: self.click(start_pos), end_port, self.rng.randint(0, 2), expect_ok=True
        )
        wire = (start_port, end_port)
        check(wire in self.wire_items(), f"no wire {drawn_key(wire)}")
        check(connections <= self.connections(), "a connection is gone")
        check(
            self.same_line(("port", start_port), ("port", end_port)),
            f"{port_key(start_port)} and {port_key(end_port)} are not on one line",
        )
        points = self.model.objects.wires.corner_points(wire)
        check(
            all(
                any(abs(x - cx) <= 1 and abs(y - cy) <= 1 for x, y in points) for cx, cy in clicks
            ),
            f"the wire {points} doesn't run through the clicks {clicks}",
        )
        after = self.routes()
        changed = [drawn_key(key) for key in before if before[key] != after.get(key)]
        check(not changed, f"other wires changed: {changed}")
        return f"wire {port_key(start_port)} -> {port_key(end_port)} corners {clicks}"

    def draw_and_abort(self) -> str:
        outputs = self.outputs()
        if not outputs:
            raise Skip("no outputs")
        start_pos = self.port_click_pos(self.rng.choice(outputs))
        self.click(start_pos)
        for _ in range(self.rng.randint(0, 3)):
            self.click(self.free_pos())
        QTest.keyClick(self.window, Qt.Key.Key_Escape)
        self.spin()
        check(not self.model.objects.new_wire.ongoing(), "Esc didn't stop the wire")
        return "draw and abort with Esc"

    def check_deleted(
        self,
        before: dict[Wire, list[tuple[float, float]]],
        connections: set[Wire],
        deleted: set[Wire],
        gone: set[Wire],
    ) -> None:
        """
        The deleted wires are gone, and the connections whose ports aren't on the same
        line any more ('gone' go anyway). The other wires keep their shape, a joined wire
        can be known by another input port of its line.
        """
        after = self.routes()
        for wire in deleted:
            check(
                wire not in after or after[wire] != before.get(wire),
                f"the deleted wire {drawn_key(wire)} is still there",
            )
        lines = self.gui_lines()[0]
        for wire in connections - self.connections() - gone:
            check(
                not lines.same(("port", wire[0]), ("port", wire[1])),
                f"{wire_key(wire)} is disconnected, but its ports are on one line",
            )
        for key, line in after.items():
            if key in before:
                check(before[key] == line, f"the wire {drawn_key(key)} changed shape")

    def drawn_segments(self) -> list[tuple[tuple[float, float], tuple[float, float]]]:
        """The segments of the wires in the GUI that have a length"""
        return [
            (start, end)
            for item in self.wire_items().values()
            for start, end in pairwise(item.corner_points())
            if start != end
        ]

    @staticmethod
    def covered(
        point: tuple[float, float],
        segments: list[tuple[tuple[float, float], tuple[float, float]]],
    ) -> bool:
        """Is a point on one of some segments"""
        return any(on_segment(start, end, point) for start, end in segments)

    def _delete_pieces(self, pos: tuple[float, float] | None) -> set[Wire]:
        """
        Delete the selected pieces of lines: what is left was drawn before, the clicked
        position ('pos') is gone unless a wire that wasn't selected runs there too, and
        a connection goes only if its ports aren't on one line any more
        """
        before = self.drawn_segments()
        kept = [
            (start, end)
            for item in self.wire_items().values()
            for part in item.part_items
            if not part.is_wire_selected()
            for start, end in [item.corner_points()[part.segment : part.segment + 2]]
            if start != end
        ]
        connections = self.connections()
        self.model.objects.delete_selected()
        self.spin()
        after = self.drawn_segments()
        for start, end in after:
            middle = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
            check(
                all(self.covered(point, before) for point in (start, middle, end)),
                f"the segment {start}-{end} wasn't drawn before",
            )
        if pos is not None and not self.covered(pos, kept):
            check(not self.covered(pos, after), f"a wire is still at {pos}")
        lines = self.gui_lines()[0]
        removed = connections - self.connections()
        for wire in removed:
            check(
                not lines.same(("port", wire[0]), ("port", wire[1])),
                f"{wire_key(wire)} is disconnected, but its ports are on one line",
            )
        return removed

    def delete_route(self) -> str:
        """A click on a wire selects the piece of the line there, between ports and dots"""
        self.clear_selection()
        part, pos = self.segment_pos()
        self.click(pos)
        runs = self.model.objects.wires.runs()
        clicked = runs.get((part._parent.wire, part.segment))
        for wire, item in self.wire_items().items():
            for other in item.part_items:
                expected = clicked is not None and runs.get((wire, other.segment)) == clicked
                if (wire, other.segment) == (part._parent.wire, part.segment):
                    expected = True
                check(
                    other.is_wire_selected() == expected,
                    f"segment {other.segment} of {drawn_key(wire)} is "
                    f"{'not ' if expected else ''}selected with the piece",
                )
        self._delete_pieces(pos)
        return f"delete the piece of {drawn_key(part._parent.wire)} segment {part.segment}"

    def delete_tree(self) -> str:
        self.clear_selection()
        part, pos = self.segment_pos()
        if self.rng.random() < 0.5:
            self.click(pos)
            # A second click on the selected segment, not on its dot
            if part._handle_at(QPointF(*pos)) is not None:
                raise Skip("on a dot after the selection")
            self.click(pos)
            how = "second click"
        else:
            state = self.context_menu(pos, "Select wire tree")
            check(state.get("Select wire tree", False), f"no Select wire tree in {state}")
            how = "menu"
        # The whole line
        expected = self.line_items(part._parent.wire)
        selected = set(self.scene._selected_wires)
        check(
            selected == expected,
            f"{how} selected {sorted(map(drawn_key, selected))}, "
            f"expected the line {sorted(map(drawn_key, expected))}",
        )
        _, ports = self.gui_lines()
        lines = self.gui_lines()[0]
        root = lines.find(("wire", part._parent.wire))
        outputs, inputs = ports.get(root, ([], []))
        self._delete_pieces(pos)
        connections = self.connections()
        left = [(o, i) for o in outputs for i in inputs if (o, i) in connections]
        check(not left, f"connections of the deleted line are left: {left}")
        return f"delete the line of {drawn_key(part._parent.wire)} by {how}"

    def delete_component(self) -> str:
        objects = self.component_objects()
        if not objects:
            raise Skip("no components")
        obj = self.rng.choice(objects)
        component = obj.component
        self.clear_selection()
        obj.setSelected(True)
        self.spin(5)
        gone = {w for w in self.connections() if component in (w[0].parent(), w[1].parent())}
        # Wires that start on a deleted wire stay, the routes of the others don't change
        before = self.routes()
        connections = self.connections()
        self.model.objects.delete_selected()
        self.spin()
        check(not gone & self.connections(), "a connection of the component is still there")
        check(
            component not in self.model.objects.circuit.get_toplevel_components(),
            "the component is still in the circuit",
        )
        self.check_deleted(before, connections, set(), gone)
        return f"delete component {component.name()}"

    def copy_paste(self) -> str:
        """Copy some components and paste them: the connections between them come along"""
        objects = self.component_objects()
        if not objects:
            raise Skip("no components")
        chosen = self.rng.sample(objects, min(len(objects), self.rng.randint(1, 3)))
        if len(objects) + len(chosen) > MAX_COMPONENTS:
            raise Skip("full")
        copied = {obj.component for obj in chosen}
        inside = {w for w in self.connections() if {w[0].parent(), w[1].parent()} <= copied}
        before = set(self.model.objects.circuit.get_toplevel_components())
        self.clear_selection()
        for obj in chosen:
            obj.setSelected(True)
        self.spin(5)
        self.area.copy_selection()
        self.area.paste()
        self.spin()
        pasted = set(self.model.objects.circuit.get_toplevel_components()) - before
        check(len(pasted) == len(copied), f"{len(pasted)} pasted of {len(copied)} copied")
        between = {w for w in self.connections() if {w[0].parent(), w[1].parent()} <= pasted}
        check(
            len(between) == len(inside),
            "the pasted components aren't connected like the copied: "
            f"{sorted(port_key(a) + '>' + port_key(b) for a, b in inside)} pasted as "
            f"{sorted(port_key(a) + '>' + port_key(b) for a, b in between)}",
        )
        outside = {
            w for w in self.connections() if (w[0].parent() in pasted) != (w[1].parent() in pasted)
        }
        check(not outside, "a pasted component is connected to another one")
        return f"copy and paste {sorted(c.name() for c in copied)}"

    def drag_segment(self) -> str:
        self.clear_selection()
        part, pos = self.segment_pos()
        self.click(pos)
        item = part._parent
        movable = [
            p
            for p in item._part_items
            if p.is_wire_selected()
            and (item.is_movable(p.segment) or item.is_port_segment(p.segment))
        ]
        if not movable:
            raise Skip("no movable segment")
        segment_item = self.rng.choice(movable)
        segment = segment_item.segment
        (x1, y1), (x2, y2) = item.corner_points()[segment : segment + 2]
        dot = self.snap(((x1 + x2) / 2, (y1 + y2) / 2))
        top = self.top_item(dot)
        if not isinstance(top, WirePartGraphicsItem) or top._handle_at(QPointF(*dot)) is None:
            raise Skip("dot covered")
        item = top._parent
        segment = top._handle_at(QPointF(*dot))
        assert segment is not None
        if self.scene._wire_point_at(QPointF(*dot)) is not None:
            raise Skip("a point closer than the dot")
        wire = item.wire
        wires = self.model.objects.wires
        tree = set(wires.tree(wire))
        # The wires that start or end on the tree follow it
        following = tree | self.attached(tree)
        others = {key: line for key, line in self.routes().items() if key not in following}
        delta = self.rng.choice([-60, -30, 30, 60])
        vertical = segment % 2 == 1
        end = self.snap((dot[0] + delta, dot[1]) if vertical else (dot[0], dot[1] + delta))
        old = list(self.model.objects.wires.path(wire))
        at_port = item.is_port_segment(segment)
        was_selected = item.is_selected()
        self.drag(dot, end)
        self.spin()
        new = self.model.objects.wires.path(wire)
        check(
            not was_selected or self.wire_items()[wire].is_selected(),
            f"{drawn_key(wire)} isn't selected after the drag",
        )
        if at_port:
            # Split next to the port: a step there, and the part away from it moved
            moving = segment + 2 if segment == 0 else segment
            check(len(new) == len(old) + 2, f"no step at the port: {old} -> {new}")
            segment = moving
        check(
            new[segment - 1] == round(end[0] if vertical else end[1]),
            f"segment {segment} of {drawn_key(wire)} not moved: {old} -> {new}",
        )
        after = self.routes()
        for key, line in others.items():
            check(after.get(key) == line, f"another tree's wire {drawn_key(key)} changed")
        return f"drag {drawn_key(wire)} segment {segment} by {delta}"

    def points(self) -> list[tuple[float, float]]:
        """The points where wires meet (the dots), and the joints of selected wires"""
        points = []
        for item in self.wire_items().values():
            for part in item.part_items:
                ring = part.ring()
                points += [*part.dots, *([ring] if ring is not None else [])]
        return list(dict.fromkeys(points))

    def _point_pos(self) -> tuple[float, float]:
        """A point where wires meet, or a joint of a selected wire, that a click hits"""
        if self.rng.random() < 0.3:
            # A wire selected first: its joints are points too
            _, pos = self.segment_pos()
            self.click(pos)
        points = self.points()
        if not points:
            raise Skip("no points")
        point = self.rng.choice(points)
        pos = self.snap(point)
        if self.scene._wire_point_at(QPointF(*pos)) != point:
            raise Skip("another point close by, or not a wire on top")
        top = self.top_item(pos)
        if isinstance(top, PortGraphicsItem | ComponentObject):
            raise Skip("point covered")
        return point

    def select_point(self) -> str:
        """
        A click on a point selects it (not its wires), the next one the wires that meet
        there, the next one the whole line, and the next one the point again
        """
        self.clear_selection()
        point = self.retry(self._point_pos)
        pos = self.snap(point)
        self.click(pos)
        check(self.scene.selected_point() == point, f"{point} is not selected")
        check(not self.scene._selected_wires, "wires are selected with the point")
        clicks = self.rng.randint(1, 3)
        if self.scene._wire_point_at(QPointF(*pos)) != point:
            # Under a component now: the wire selected before the click was on top
            return f"select point {point}, covered then"
        for _ in range(clicks - 1):
            self.click(pos)
        lines, _ = self.gui_lines()
        items = self.wire_items()
        # The line with the dot or the joint: another one can have a corner there too
        marked = {
            lines.find(("wire", wire))
            for wire, item in items.items()
            if any(point in part.dots or part.ring() == point for part in item.part_items)
        }
        cornered = [wire for wire, item in items.items() if point in item.corner_points()]
        owner = next(
            (wire for wire in cornered if lines.find(("wire", wire)) in marked), cornered[0]
        )
        if clicks == 2:
            # The wires of the point's line there
            attached = {
                wire
                for wire, item in items.items()
                if lines.same(("wire", wire), ("wire", owner))
                and any(part.touches(point) for part in item.part_items)
            }
            check(self.scene.selected_point() is None, "the point is still selected")
            check(
                attached <= self.scene._selected_wires,
                f"the wires at {point} are not selected: "
                f"{sorted(map(drawn_key, attached - self.scene._selected_wires))}",
            )
        if clicks == 3:
            line = self.line_items(owner)
            selected = self.scene._selected_wires
            check(
                selected == line,
                f"the third click on {point} doesn't select the whole line: missing "
                f"{sorted(map(drawn_key, line - selected))}, also "
                f"{sorted(map(drawn_key, selected - line))}",
            )
        return f"select point {point} with {clicks} clicks"

    def drag_point(self) -> str:
        """
        Drag a point where wires meet, or a joint, along the straight line through it,
        between the corners on each side. The wires there follow it, the others don't
        change. A point that can't move stays.
        """
        self.clear_selection()
        point = self.retry(self._point_pos)
        start = self.snap(point)
        wires = self.model.objects.wires
        move = wires.point_move(point)
        axis = 0 if move is None or move.segment % 2 == 1 else 1
        delta = self.rng.choice([-80, -40, -15, 15, 40, 80])
        end = list(start)
        end[axis] += delta
        before = self.routes()
        attached = set() if move is None else {move.wire} | self.attached({move.wire})
        self.drag(start, (end[0], end[1]))
        self.spin()
        after = self.routes()
        if move is None:
            check(after == before, f"{point} can't move, but the wires changed")
            return f"drag point {point}, can't move"
        expected = min(max(round(start[axis] + delta), move.bounds[0]), move.bounds[1])
        moved = (expected, point[1]) if axis == 0 else (point[0], expected)
        check(
            any(moved in item.corner_points() for item in self.wire_items().values()),
            f"no point at {moved} after moving {point}",
        )
        check(self.scene.selected_point() == moved, f"{moved} is not selected after the drag")
        changed = [
            drawn_key(key)
            for key in before
            if key not in attached and before[key] != after.get(key)
        ]
        check(not changed, f"other wires changed: {changed}")
        return f"drag point {point} of {drawn_key(move.wire)} to {moved}"

    def _finish_started_wire(
        self,
        wire: Wire,
        pos: tuple[float, float],
        old: list[float],
        old_routes: dict[Wire, list[tuple[float, float]]],
    ) -> str:
        """
        A wire started from the context menu: aborted with Esc, nothing changes, or
        drawn to a free input port, a branch from where the menu was opened
        """
        wires = self.model.objects.wires
        new_wire = self.model.objects.new_wire
        check(new_wire.ongoing(), "Start wire here didn't start a wire")
        check(wires.path(wire) == old, "starting a wire changed the wire")
        branch = new_wire.start_branch()
        assert branch is not None
        start = wires.anchor_point(*branch)
        check(
            abs(start[0] - pos[0]) <= 1 and abs(start[1] - pos[1]) <= 1,
            f"the wire starts at {start}, not at {pos}",
        )
        inputs = self.free_inputs(wire[0].width, branch[0])
        port_pos = None
        if inputs and self.rng.random() < 0.6:
            dst_port = self.rng.choice(inputs)
            try:
                port_pos = self.port_click_pos(dst_port)
            except Skip:
                port_pos = None
        if port_pos is None:
            QTest.keyClick(self.window, Qt.Key.Key_Escape)
            self.spin()
            check(not new_wire.ongoing(), "Esc didn't stop the wire")
            check(wires.path(wire) == old, "an aborted wire changed the wire")
            check(self.routes() == old_routes, "an aborted wire changed the wires")
            return f"start a wire on {drawn_key(wire)} at {pos}, aborted"
        self.click(port_pos)
        self.spin()
        check(not new_wire.ongoing(), "the wire wasn't finished")
        new = (branch[0][0], dst_port)
        check(new in self.wire_items(), f"no wire {drawn_key(new)}")
        anchor = wires.branch(new)
        check(anchor is not None and anchor[0] == branch[0], f"starts on {anchor}")
        points = wires.corner_points(new)
        check(points[0] == start, f"the branch starts at {points[0]}, not at {start}")
        return f"start a wire on {drawn_key(wire)} at {pos} to {port_key(dst_port)}"

    def edit_segment(self) -> str:
        self.clear_selection()
        part, pos = self.segment_pos()
        item = part._parent
        wire = item.wire
        wires = self.model.objects.wires
        old = list(wires.path(wire))
        old_routes = self.routes()
        joint = wires.unused_joint(wire, part.segment)
        text = self.rng.choice(
            ["Split segment", "Start wire here", "Merge segments", "Automatic route"]
        )
        state = self.context_menu(pos, text)
        check(text in state, f"no {text} in the menu {state}")
        if text != "Start wire here":
            # Not while a new wire is drawn from it
            check(
                wire in self.scene._selected_wires,
                "the wire is not selected after the right-click",
            )
        new = wires.path(wire)
        if not state[text]:
            check(new == old, f"{text} was disabled but the wire changed")
            return f"{text} (disabled) on {drawn_key(wire)}"
        if text == "Split segment":
            check(len(new) == len(old) + 2, f"split: {old} -> {new}")
        elif text == "Start wire here":
            return self._finish_started_wire(wire, pos, old, old_routes)
        elif text == "Merge segments" and joint is not None:
            # Without the joint, in the same place: the only vertical segment of a
            # straight wire goes to its end instead
            check(self.routes()[wire] == old_routes[wire], f"joint removed: {old} -> {new}")
        elif text == "Merge segments":
            check(len(new) == len(old) - 2, f"merge: {old} -> {new}")
        else:
            check(new == wires.automatic_path(wire), "not the automatic route")
        return f"{text} on {drawn_key(wire)} segment {part.segment}"

    def move_component(self) -> str:
        objects = self.component_objects()
        if not objects:
            raise Skip("no components")
        obj = self.rng.choice(objects)
        rect = obj.rect().translated(obj.pos())
        pos = self.snap((rect.center().x(), rect.center().y()))
        if self.top_item(pos) is not obj:
            raise Skip("component covered")
        delta = (self.rng.choice([-40, -20, 20, 40]), self.rng.choice([-40, -20, 20, 40]))
        before = (obj.pos().x(), obj.pos().y())
        self.clear_selection()
        # Sometimes a group: more selected components that move with it
        others = [other for other in objects if other is not obj]
        group = [obj, *self.rng.sample(others, min(len(others), self.rng.choice([0, 0, 1, 3])))]
        for member in group:
            member.setSelected(True)
        moving = {member.component for member in group}
        wires = self.model.objects.wires

        def between(wire: Wire) -> bool:
            """Between components that move together, or from one to a line that moves"""
            joint = wires.join(wire)
            if joint is not None:
                return wire[0].parent() in moving and between(joint[0])
            return wire[0].parent() in moving and wire[1].parent() in moving

        old_paths = {wire: (list(wires.path(wire)), between(wire)) for wire in wires.drawn()}
        # The wires that leave a port up or down follow it across
        follows = wires.following_ends(moving, wires.moving_wires(moving))
        self.drag(pos, (pos[0] + delta[0], pos[1] + delta[1]))
        after = (obj.pos().x(), obj.pos().y())
        check(after != before, f"{obj.component.name()} didn't move")
        moved = (round(after[0] - before[0]), round(after[1] - before[1]))
        for wire in wires.drawn():
            old, between = old_paths[wire]
            # The wires between components that move together move with them
            expected = [
                value + (moved[index % 2] if between else 0) for index, value in enumerate(old)
            ]
            if wire in follows:
                _, start, end = follows[wire]
                if start:
                    expected[0] += moved[0]
                if end:
                    expected[-1] += moved[0]
            check(
                wires.path(wire) == expected,
                f"{drawn_key(wire)}: {old} -> {wires.path(wire)}, not {expected}",
            )
        names = "+".join(member.component.name() for member in group)
        return f"move {names} by {delta}"

    def rotate_component(self) -> str:
        """Rotate a component a quarter, like Rotate in its context menu or the Edit menu"""
        objects = [obj for obj in self.component_objects() if obj.ROTATABLE]
        if not objects:
            raise Skip("no component that can be rotated")
        obj = self.rng.choice(objects)
        before = obj.rotation_angle
        center = obj.mapRectToScene(obj.rect()).center()
        self.model.objects.components.rotate([obj])
        self.spin()
        check(obj.rotation_angle == (before + 90) % 360, f"{obj.component.name()} didn't rotate")
        after = obj.mapRectToScene(obj.rect()).center()
        check(after == center, f"{obj.component.name()} moved when it rotated")
        wires = self.model.objects.wires
        for wire in wires.drawn():
            src_port, dst_port = wire
            at_start = wires.branch(wire) is None and src_port.parent() is obj.component
            at_end = wires.join(wire) is None and dst_port.parent() is obj.component
            if at_start or at_end:
                check(
                    wires.path(wire) == wires.automatic_path(wire),
                    f"{drawn_key(wire)}: not the automatic path after the rotation",
                )
                if wires._turned_ends(wire) is not None:
                    self.check_turned_ends(wire)
        return f"rotate {obj.component.name()} to {obj.rotation_angle}"

    def flip_component(self) -> str:
        """Mirror a component, like Flip Horizontal or Flip Vertical in the Edit menu"""
        objects = [obj for obj in self.component_objects() if obj.ROTATABLE]
        if not objects:
            raise Skip("no component that can be mirrored")
        obj = self.rng.choice(objects)
        horizontal = self.rng.random() < 0.5
        before = (obj.rotation_angle, obj.flipped)
        center = obj.mapRectToScene(obj.rect()).center()
        self.model.objects.components.flip([obj], horizontal)
        self.spin()
        expected = (((180 if horizontal else 0) - before[0]) % 360, not before[1])
        check((obj.rotation_angle, obj.flipped) == expected, f"{obj.component.name()} flip")
        check(obj.mapRectToScene(obj.rect()).center() == center, "moved when mirrored")
        wires = self.model.objects.wires
        for wire in wires.drawn():
            src_port, dst_port = wire
            at_start = wires.branch(wire) is None and src_port.parent() is obj.component
            at_end = wires.join(wire) is None and dst_port.parent() is obj.component
            if (at_start or at_end) and wires._turned_ends(wire) is not None:
                self.check_turned_ends(wire)
        way = "horizontally" if horizontal else "vertically"
        return f"flip {obj.component.name()} {way}"

    def undo(self) -> str:
        if not self.history:
            raise Skip("nothing to undo")
        expected = self.history[-1]
        current = self.snapshot()
        self.model.objects.undo()
        self.spin()
        check(self.snapshot() == expected, "undo didn't restore the state before the change")
        self.history.pop()
        self.future.append(current)
        return "undo"

    def undo_while_dragging(self) -> str:
        """
        An undo while a point is dragged (the mouse button still held): the undo is done,
        and the rest of the drag does nothing
        """
        if not self.history:
            raise Skip("nothing to undo")
        self.clear_selection()
        point = self.retry(self._point_pos)
        start = self.snap(point)
        expected = self.history[-1]
        current = self.snapshot()
        self.press(start)
        self.move((start[0] + 20, start[1]))
        self.move((start[0] + 20, start[1] + 20))
        self.model.objects.undo()
        self.spin()
        self.move((start[0] + 40, start[1] + 40))
        self.release((start[0] + 40, start[1] + 40))
        self.spin()
        check(self.snapshot() == expected, "the drag changed the circuit after the undo")
        self.history.pop()
        self.future.append(current)
        return f"undo while dragging {point}"

    def redo(self) -> str:
        if not self.future:
            raise Skip("nothing to redo")
        expected = self.future[-1]
        current = self.snapshot()
        self.model.objects.redo()
        self.spin()
        check(self.snapshot() == expected, "redo didn't restore the undone change")
        self.future.pop()
        self.history.append(current)
        return "redo"

    def file_snapshot(self) -> Any:
        """
        What a circuit file keeps: the components, connections, and the shape of each
        line. Not the drawn wires, a joined wire can be a branch after loading.
        """
        gui = self.model.objects.components.get_gui_dict()
        components = {name: (pos.x, pos.y, pos.rotation, pos.flipped) for name, pos in gui.items()}
        connections = sorted(
            (port_key(src_port), port_key(dst_port)) for src_port, dst_port in self.connections()
        )
        ports = {port_key(port): port for port in self.model.objects.wires.ports()}
        shapes = set()
        for line in self.model.objects.wires.to_lines():

            def place(node: str, line: Any = line) -> tuple[float, float]:
                return self.port_pos(ports[node]) if node in ports else tuple(line.points[node])

            segments = frozenset(frozenset((place(a), place(b))) for a, b in line.segments)
            shapes.add((frozenset(line.ports), segments))
        return components, connections, shapes

    def save_and_load(self) -> str:
        """
        Save As (the file dialog gives the file), and load the file again. Not with the
        Load button: a file that is open already only gets its tab shown.
        """
        path = self.out_dir / "fuzz.circuit"
        before = self.file_snapshot()
        dialogs = QFileDialog.getSaveFileName, QFileDialog.getOpenFileName
        chosen = staticmethod(lambda *args, **kwargs: (str(path), ""))
        QFileDialog.getSaveFileName = chosen  # type: ignore[method-assign]
        QFileDialog.getOpenFileName = chosen  # type: ignore[method-assign]
        menu_bar = self.window.menuBar()
        assert isinstance(menu_bar, MenuBar)
        try:
            # Save As: Save writes to the file the circuit came from, like an example
            menu_bar.save_circuit_as()
            check(not self.model.is_changed, "the circuit is changed after it was saved")
            check(not menu_bar._save_action.isEnabled(), "Save is on after saving")
            saved = path.read_text()
            check('"lines"' in saved or not self.connections(), "the file has no lines")
            check('"wires"' not in saved, "the file has the wires of the old format")
            self.model.load_circuit(path)
        finally:
            QFileDialog.getSaveFileName, QFileDialog.getOpenFileName = dialogs  # type: ignore[method-assign]
        self.spin(50)
        check(not self.model.objects.can_undo(), "undo steps from before the load")
        check(self.file_snapshot() == before, "the loaded circuit differs from the saved one")
        self.history.clear()
        self.future.clear()
        return "save and load"

    def wait_stopped(self, steps: int = 500) -> bool:
        """
        Until the simulation thread has stopped and the GUI knows it (Start is on again),
        False if it runs after some steps
        """
        controls = self.window.findChild(SimControlWidget)
        assert controls is not None
        for _ in range(steps):
            if not self.model.is_running and controls._start_button.isEnabled():
                return True
            self.spin(10)
        check(steps < 500, "the simulation didn't stop")
        return False

    def check_vcd(self, path: Path) -> None:
        """A VCD file that was closed has its header and the times"""
        text = path.read_text()
        check("$enddefinitions" in text, f"{path.name} has no header: {text[:200]!r}")
        check("#0" in text, f"{path.name} has no time 0")

    def set_vcd(self, enable: bool) -> Path | None:
        """Turn the VCD output on (to a new file) or off with its checkbox"""
        widget = self.window.findChild(VcdControlWidget)
        assert widget is not None
        if not enable:
            path = widget._vcd_filename
            was_on = widget._enable_vcd.isChecked()
            widget._enable_vcd.setChecked(False)
            self.spin()
            if was_on and path is not None:
                self.check_vcd(Path(path))
            return None
        self.vcd_files += 1
        path = self.out_dir / f"fuzz{self.vcd_files}.vcd"
        # As if chosen in the file dialog
        widget._vcd_filename = str(path)
        if widget._enable_vcd.isChecked():
            widget._start_vcd(str(path))
        else:
            widget._enable_vcd.setChecked(True)
        self.spin()
        check(path.exists(), "the VCD file wasn't created")
        return path

    def toggle_inputs(self) -> int:
        """Click buttons and switches, as while the simulation runs"""
        clicked = 0
        for obj in self.component_objects():
            if obj.component.has_action and self.rng.random() < 0.5:
                center = obj.rect().translated(obj.pos()).center()
                pos = (center.x(), center.y())
                if self.top_item(pos) is obj:
                    self.click(pos)
                    clicked += 1
        return clicked

    def start_stop(self, controls: SimControlWidget) -> None:
        """Start or stop the simulation, with the button or with Space"""
        if self.rng.random() < 0.5:
            controls._start_button.click()
        else:
            QTest.keyClick(self.area, Qt.Key.Key_Space)

    def wait_running_or_stopped(self) -> None:
        """Until a start or a stop is done, and the GUI knows it"""
        controls = self.window.findChild(SimControlWidget)
        assert controls is not None
        for _ in range(500):
            stopping = not self.model._keep_running and self.model.isRunning()
            if not stopping and controls._start_button.isEnabled():
                return
            self.spin(10)
        raise FuzzFailure("the simulation didn't start or stop")

    def run_simulation(self) -> str:
        before = self.snapshot()
        controls = self.window.findChild(SimControlWidget)
        assert controls is not None
        vcd = self.rng.random() < 0.5
        vcd_path = self.set_vcd(True) if vcd else None
        if self.rng.random() < 0.3:
            controls._single_step_button.click()
            # Until the next event: in a circuit where nothing happens, until it is stopped
            if not self.wait_stopped(50):
                controls._start_button.click()
                self.wait_stopped()
        if self.rng.random() < 0.3:
            # Start and stop quickly, with the button and with Space, without waiting
            for _ in range(self.rng.randint(1, 4)):
                self.start_stop(controls)
                self.spin(self.rng.randint(0, 3))
            self.wait_running_or_stopped()
            if self.model.is_running:
                self.start_stop(controls)
            self.wait_stopped()
        self.start_stop(controls)
        self.spin(self.rng.randint(30, 200))
        check(self.model.is_running, "the simulation didn't start")
        clicked = self.toggle_inputs()
        self.spin(self.rng.randint(10, 100))
        items = list(self.wire_items().values())
        if items:
            item = self.rng.choice(items)
            self.click(item.corner_points()[1])
            check(
                not self.model.objects.new_wire.ongoing(),
                "a wire was started while the simulation runs",
            )
        # The keys that change the circuit don't while it runs
        self.model.objects.delete_selected()
        for key in (Qt.Key.Key_Z, Qt.Key.Key_Y):
            QTest.keyClick(self.area, key, Qt.KeyboardModifier.ControlModifier)
        QTest.keyClick(self.area, Qt.Key.Key_Delete)
        self.spin()
        self.check_painted()
        self.start_stop(controls)
        self.wait_stopped()
        self.spin(30)
        if self.rng.random() < 0.5:
            controls._reset_button.click()
            self.spin()
            check(self.model.objects.circuit.time_ns == 0, "reset didn't go to time 0")
        if vcd_path is not None and self.rng.random() < 0.6:
            self.set_vcd(False)
        check(self.snapshot() == before, "the circuit changed while the simulation ran")
        return f"run the simulation (vcd={vcd}, {clicked} inputs clicked)"

    def zoom(self) -> str:
        """Zoom in or out and look around, check what is painted, and zoom back"""
        steps = self.rng.choice([-3, -2, -1, 1, 2])
        for _ in range(abs(steps)):
            if steps > 0:
                self.model.zoom_in()
            else:
                self.model.zoom_out()
        self.area.centerOn(
            QPointF(
                self.rng.uniform(0, GRID_COLUMNS * CELL_WIDTH),
                self.rng.uniform(0, GRID_ROWS * CELL_HEIGHT),
            )
        )
        self.spin()
        self.check_painted()
        # The other actions click at whole scene positions
        self.area.resetTransform()
        self.spin()
        return f"zoom {steps:+d} and back"

    def load_example(self) -> str:
        """Load an example circuit: many components, ICs and Yosys components"""
        if not EXAMPLE_CIRCUITS:
            raise Skip("no example circuits")
        path = self.rng.choice(EXAMPLE_CIRCUITS)
        self.model.load_circuit(path)
        self.spin(100)
        check(not self.errors[-1:] or "Could not" not in self.errors[-1], str(self.errors[-1:]))
        self.history.clear()
        self.future.clear()
        return f"load {path.name}"

    def clear_circuit(self) -> str:
        """Start over with an empty circuit (an undo step)"""
        if not self.component_objects():
            raise Skip("empty")
        if self.rng.random() < 0.7:
            # Seldom, the circuit should grow too
            raise Skip("not this time")
        self.model.clear_circuit()
        self.spin()
        return "clear the circuit"

    ACTIONS: ClassVar[list[tuple[str, int]]] = [
        ("add_component", 4),
        ("connect_ports", 6),
        ("connect_from_corner", 4),
        ("connect_to_corner", 3),
        ("connect_to_segment", 3),
        ("connect_shared", 6),
        ("connect_join", 5),
        ("connect_join_from_line", 4),
        ("connect_lines", 4),
        ("connect_same_kind", 4),
        ("drag_point", 4),
        ("select_point", 3),
        ("connect_invalid", 1),
        ("draw_and_abort", 1),
        ("delete_route", 3),
        ("delete_tree", 1),
        ("delete_component", 2),
        ("drag_segment", 3),
        ("edit_segment", 3),
        ("move_component", 2),
        ("rotate_component", 2),
        ("flip_component", 2),
        ("copy_paste", 2),
        ("undo", 3),
        ("undo_while_dragging", 1),
        ("redo", 2),
        ("save_and_load", 1),
        ("run_simulation", 2),
        ("zoom", 1),
        ("load_example", 1),
        ("clear_circuit", 1),
    ]
    # These don't change the circuit by themselves, or check undo themselves
    NO_UNDO_CHECK: ClassVar[set[str]] = {
        "undo",
        "undo_while_dragging",
        "redo",
        "save_and_load",
        "run_simulation",
        "zoom",
        "load_example",
    }

    def step(self, number: int) -> None:
        """One random action, and the checks after it"""
        actions = dict(self.ACTIONS)
        # Undo and redo when there is something to undo or redo, redo mostly after an undo
        if not self.history:
            del actions["undo"]
            del actions["undo_while_dragging"]
        if self.future:
            actions["redo"] = 5
        else:
            del actions["redo"]
        names, weights = list(actions), list(actions.values())
        # A new (or cleared) circuit starts with a few components
        few = number < 4 or len(self.component_objects()) < 2
        name = "add_component" if few else self.rng.choices(names, weights)[0]
        stack = self.model.objects._undo_stack
        before = self.snapshot()
        top = stack[-1] if stack else None
        length = len(stack)
        try:
            text = getattr(self, name)()
        except FuzzFailure as failure:
            raise FuzzFailure(f"{name}: {failure}") from failure
        except Skip as reason:
            self.counts["skipped"] += 1
            if self.verbose:
                print(f"{number}: skip {name}: {reason}")
            # A skipped action must not have changed anything
            if self.model.objects.new_wire.ongoing():
                self.model.model_abort_wire()
            if self.snapshot() != before:
                raise FuzzFailure(f"{name} changed the circuit and was skipped: {reason}")
            return
        self.log.append(f"{number}: {text}")
        if self.verbose:
            print(self.log[-1])
        self.counts[name] += 1
        self.most = max(self.most, len(self.component_objects()))
        self.check_invariants()
        if name in self.NO_UNDO_CHECK:
            return
        after = self.snapshot()
        pushed = len(stack) != length or (bool(stack) and stack[-1] is not top)
        changed = after != before
        check(not (changed and not pushed), f"{name} changed the circuit without an undo step")
        check(not (pushed and not changed), f"{name} added an undo step without a change")
        if changed:
            self.history = [*self.history, before][-UNDO_DEPTH:]
            self.future.clear()

    def save_failure(self) -> Path:
        """Save the circuit as it is when a check failed"""
        path = self.out_dir / f"failure_seed{self.seed}.circuit"
        try:
            self.model.save_circuit(path)
        except Exception as exc:  # noqa: BLE001 - the circuit may be broken
            print(f"could not save the circuit: {exc}")
        return path


def set_max_components(count: int) -> None:
    """Room for more components: a grid with a cell for each, and some to spare"""
    global MAX_COMPONENTS, GRID_COLUMNS, GRID_ROWS
    MAX_COMPONENTS = count
    while GRID_COLUMNS * GRID_ROWS < count * 3 // 2:
        GRID_COLUMNS += 1
        GRID_ROWS = max(GRID_ROWS, GRID_COLUMNS * 2 // 3)


def run_seeds(seeds: list[int], steps: int, jobs: int, extra: list[str]) -> int:
    """
    Run seeds in parallel processes, and print one line for each: OK, or the failure
    and how to repeat it
    """

    def run(seed: int) -> list[str]:
        command = [sys.executable, __file__, "--seed", str(seed), "--steps", str(steps), *extra]
        try:
            # A step takes a fraction of a second: much longer is a hang
            result = subprocess.run(
                command, capture_output=True, text=True, check=False, timeout=120 + steps
            )
        except subprocess.TimeoutExpired:
            return [f"gui_fuzz HUNG seed={seed}: no result after {120 + steps} s"]
        lines = result.stdout.splitlines()
        found = [line for line in lines if line.startswith("gui_fuzz ")]
        if not found:
            error = (result.stderr.strip().splitlines() or ["no output"])[-1]
            return [f"gui_fuzz CRASHED seed={seed}: {error}"]
        if result.returncode != 0 and found[0].startswith("gui_fuzz OK"):
            error = (result.stderr.strip().splitlines() or ["no output"])[-1]
            return [f"gui_fuzz CRASHED seed={seed} at exit (status {result.returncode}): {error}"]
        return found + [line for line in lines if line.startswith("repeat with:")]

    failed = False
    # Imported by name: Python 3.15 imports concurrent.futures.ThreadPoolExecutor lazily,
    # and with PySide6 6.12 loaded that attribute stays an unresolved lazy import
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        for output in pool.map(run, seeds):
            failed = failed or not output[0].startswith("gui_fuzz OK")
            print("\n".join(output), flush=True)
    return 1 if failed else 0


def quiet_qt() -> None:
    """Without the offscreen platform's warnings about what it doesn't support"""

    def handler(mode: QtMsgType, context: QMessageLogContext, message: str) -> None:
        if "This plugin does not support" not in message:
            print(message, file=sys.stderr)

    qInstallMessageHandler(handler)


def main() -> int:
    """Run the fuzzer"""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--seed", type=int, default=None, help="random seed (default: random)")
    parser.add_argument(
        "--seeds",
        type=lambda text: [int(seed) for seed in text.split(",")],
        default=None,
        help="several seeds, like 3,11,21: run in parallel, one line each",
    )
    parser.add_argument(
        "--jobs", type=int, default=os.cpu_count() or 4, help="parallel runs for --seeds"
    )
    parser.add_argument("--steps", type=int, default=300, help="number of actions")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="print every action, and their counts"
    )
    parser.add_argument("--out", type=Path, default=None, help="folder for saved circuits")
    parser.add_argument(
        "--max-components",
        type=int,
        default=MAX_COMPONENTS,
        help=f"the most components that are added (default {MAX_COMPONENTS})",
    )
    args = parser.parse_args()
    if args.seeds:
        extra = ["--max-components", str(args.max_components)]
        return run_seeds(args.seeds, args.steps, args.jobs, extra)
    set_max_components(args.max_components)
    # Without a window on the screen (set before the QApplication is created)
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    # Settings of their own, not the recent files of the user
    os.environ.setdefault("DIGSIM_SETTINGS_DIR", tempfile.mkdtemp(prefix="digsim_settings_"))
    quiet_qt()
    seed = args.seed if args.seed is not None else random.randrange(1_000_000)
    out_dir = args.out or Path(tempfile.mkdtemp(prefix="gui_fuzz_"))
    out_dir.mkdir(parents=True, exist_ok=True)
    fuzzer = GuiFuzzer(seed, args.verbose, out_dir)
    try:
        return run_steps(fuzzer, seed, args.steps)
    finally:
        fuzzer.close()


def run_steps(fuzzer: GuiFuzzer, seed: int, steps: int) -> int:
    """Run the steps of a seed, and print the result"""
    start = time.perf_counter()
    number = 0
    try:
        for number in range(steps):
            fuzzer.step(number)
    except FuzzFailure as failure:
        print(f"gui_fuzz FAILED seed={seed} step={number}: {failure}")
        print("last actions:")
        for line in fuzzer.log[-15:]:
            print(f"  {line}")
        print(f"circuit saved to {fuzzer.save_failure()}")
        print(
            f"repeat with: uv run python tools/gui_fuzz.py --seed {seed} --steps {number + 1} -v"
        )
        return 1
    elapsed = time.perf_counter() - start
    print(f"gui_fuzz OK seed={seed} steps={steps} ({elapsed:.0f} s)")
    if fuzzer.verbose:
        components = len(fuzzer.component_objects())
        wires = len(fuzzer.wire_items())
        counts = " ".join(f"{name}={count}" for name, count in sorted(fuzzer.counts.items()))
        print(f"end: {components} components {wires} wires, most {fuzzer.most}. {counts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
