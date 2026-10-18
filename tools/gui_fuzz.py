# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""
A randomized test of the GUI circuit editor, run offscreen with real mouse events

It builds a circuit from scratch: it adds components, draws wires (single bits and buses,
from output and input ports, with corners, and from corners of other wires), selects and
deletes wires, wire trees and components, drags, splits and merges segments, moves
components, undoes and redoes, and saves and loads the circuit. After each step it checks
that the GUI matches the circuit, and that exactly what should change, changed.
Components are added through the model, like the GUI does after its settings dialog.

    uv run python tools/gui_fuzz.py                  # random seed, printed
    uv run python tools/gui_fuzz.py --seed 7 --steps 500 -v

The output is one line when all is well. On a failure it prints the seed, the step, the
last actions and the failed check, saves the circuit, and exits with status 1. A run with
the same seed repeats the same actions.
"""

from __future__ import annotations

import argparse
import os
import random
import sys
import tempfile
import time
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any, ClassVar

from PySide6.QtCore import QEvent, QEventLoop, QPointF, Qt, QTimer
from PySide6.QtGui import QContextMenuEvent, QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QGraphicsItem, QMenu

from digsim.app._wire_path import (
    X_OFFSET,
    arrival_offset,
    corner_directions,
    drawing_points,
    exits_vertically,
    is_forwards,
)
from digsim.app.gui import MainWindow
from digsim.app.gui._circuit_area import (
    CircuitArea,
    WireGraphicsItem,
    WirePartGraphicsItem,
)
from digsim.app.gui_objects import ComponentObject
from digsim.app.gui_objects._component_port_item import PortGraphicsItem
from digsim.app.model import AppModel
from digsim.app.model._model_wires import port_key
from digsim.circuit.components.atoms import Port


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
    ("LedBar", {"width": 4}),
    ("HexDigit", {"digits": 1, "dot": False}),
    ("Wires2Bus", {"width": 4}),
    ("Bus2Wires", {"width": 4}),
]
# Components are placed in the cells of a grid, so that they don't overlap
GRID_COLUMNS, GRID_ROWS = 6, 4
CELL_WIDTH, CELL_HEIGHT = 240, 200
MAX_COMPONENTS = 14
UNDO_DEPTH = 100


class FuzzFailure(Exception):
    """A check failed"""


class Skip(Exception):
    """The action can't be done in this state, like a click that would hit another item"""


def check(condition: bool, message: str) -> None:
    """Fail with a message"""
    if not condition:
        raise FuzzFailure(message)


def simplify(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """The corners of a line, without repeated points and points in the middle of a line"""
    result: list[tuple[float, float]] = []
    for point in [(round(x, 1), round(y, 1)) for x, y in points]:
        if result and result[-1] == point:
            continue
        if len(result) >= 2:
            (x1, y1), (x2, y2) = result[-2], result[-1]
            if x1 == x2 == point[0] or y1 == y2 == point[1]:
                result[-1] = point
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
        self.window.resize(1700, 1100)
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
        self.spin(200)

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

    def wire_items(self) -> dict[Port, WireGraphicsItem]:
        """The wire items, by the input port they drive (in a fixed order, for the seed)"""
        items = [item for item in self.scene.items() if isinstance(item, WireGraphicsItem)]
        return {item.dst_port: item for item in sorted(items, key=lambda i: port_key(i.dst_port))}

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

    def snapshot(self) -> Any:
        """What undo must restore: the components, connections, wires' lines and paths"""
        gui = self.model.objects.components.get_gui_dict()
        components = {name: (pos.x, pos.y) for name, pos in gui.items()}
        connections = sorted(
            (port_key(src_port), port_key(dst_port)) for src_port, dst_port in self.connections()
        )
        routes = {
            port_key(dst_port): simplify(self.route(item))
            for dst_port, item in self.wire_items().items()
        }
        # The paths too: a change can keep the line, like merging a step without length
        paths = self.model.objects.wires.to_dict()
        return components, connections, routes, paths

    def routes(self) -> dict[str, list[tuple[float, float]]]:
        """The line of each wire, from the output port to the input port"""
        return self.snapshot()[2]

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
        for component in toplevel:
            for port in component.ports:
                driver = port.get_driver() if not port.is_output() else None
                check(
                    driver is None or driver.parent() in toplevel,
                    f"{port_key(port)} is driven by a deleted component",
                )
                for wired in port.wired_ports if port.is_output() else []:
                    check(wired.parent() in toplevel, f"{port_key(port)} drives a deleted port")
        items = self.wire_items()
        wire_items = [i for i in self.scene.items() if isinstance(i, WireGraphicsItem)]
        check(len(wire_items) == len(items), "two wire items drive the same input port")
        gui = {(item._src_port, dst_port) for dst_port, item in items.items()}
        connections = self.connections()
        check(
            gui == connections,
            "GUI wires != circuit connections: "
            + str(sorted(f"{port_key(s)}->{port_key(d)}" for s, d in gui ^ connections)),
        )
        for part in [i for i in self.scene.items() if isinstance(i, WirePartGraphicsItem)]:
            check(part.parentItem() in wire_items, "a wire segment without its wire")
        wires = self.model.objects.wires
        check(
            set(wires.to_dict()) == {port_key(d) for _, d in connections},
            "the saved wires are not the connections",
        )
        for dst_port, item in items.items():
            name = port_key(dst_port)
            points = item.corner_points()
            check(len(item._path) % 2 == 1, f"{name}: invalid path {item._path}")
            check(points == wires.corner_points(dst_port), f"{name}: GUI and model differ")
            check(points[-1] == self.port_pos(dst_port), f"{name}: doesn't end at its port")
            branch = wires.branch(dst_port)
            if branch is None:
                check(item._branch is None, f"{name}: a branch in the GUI only")
                check(
                    points[0] == self.port_pos(item._src_port),
                    f"{name}: doesn't start at its output port",
                )
            else:
                parent, corner = branch
                check(
                    item._branch is not None and item._branch[0].dst_port == parent,
                    f"{name}: starts on another wire in the GUI",
                )
                check(
                    parent.get_driver() is item._src_port,
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
                    port_key(dst_port) not in [port_key(w) for w in wires.route(parent)],
                    f"{name}: starts on itself",
                )
        selected = self.scene._selected_wires
        check(selected <= set(items), "a deleted wire is selected")

    # Choices

    def free_inputs(self, width: int | None = None) -> list[Port]:
        """Input ports without a driver"""
        return [
            port
            for obj in self.component_objects()
            for port in obj.component.inports()
            if not port.has_driver() and (width is None or port.width == width)
        ]

    def outputs(self) -> list[Port]:
        """All output ports"""
        return [port for obj in self.component_objects() for port in obj.component.outports()]

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

    def segment_pos(self) -> tuple[WirePartGraphicsItem, tuple[float, float]]:
        """A position on a random wire segment, and the segment that a click there hits"""
        return self.retry(self._segment_pos)

    def _segment_pos(self) -> tuple[WirePartGraphicsItem, tuple[float, float]]:
        items = list(self.wire_items().values())
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
        # Not at a corner (that starts a wire) or a dot (that drags)
        if top._corner_at(QPointF(*pos)) is not None or top._handle_at(QPointF(*pos)) is not None:
            raise Skip("on a corner or a dot")
        return top, pos

    def clear_selection(self) -> None:
        """Select nothing"""
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
        self, dst_port: Port, clicks: list[tuple[float, float]], from_source: bool
    ) -> None:
        """
        A finished wire has the shape it was drawn with: across to each click and up or
        down to it, and then to the other end, with its last bend just before that end
        """
        wires = self.model.objects.wires
        points = wires.corner_points(dst_port)
        if (
            not clicks
            and not is_forwards(points[0], points[-1])
            and wires.branch(dst_port) is None
        ):
            # Backwards without clicks: the automatic route around the component
            return
        branch = wires.branch(dst_port)
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
        elif branch is not None:
            # A wire reaches another wire without the step that a port needs, unless it
            # would reach it along the other wire
            taken = wires.taken_directions(*branch)
            step = arrival_offset(taken, end, drawn[-3])
        else:
            step = X_OFFSET
        expected = [*drawn[:-2], (end[0] + step, drawn[-3][1]), (end[0] + step, end[1]), end]
        check(points == expected, f"the wire doesn't keep its drawn shape: {points} != {expected}")

    def check_across(self, dst_port: Port) -> None:
        """A new branch leaves (or reaches) a joint across the wire, not along it"""
        wires = self.model.objects.wires
        branch = wires.branch(dst_port)
        check(branch is not None, f"{port_key(dst_port)} is not a branch")
        assert branch is not None
        taken = wires.taken_directions(*branch)
        if taken not in ({"left", "right"}, {"up", "down"}):
            return  # a corner: the user's clicks may lead along the wire
        start, *rest = wires.corner_points(dst_port)
        other = next(point for point in rest if point != start)
        if other[0] != start[0]:
            way = "right" if other[0] > start[0] else "left"
        else:
            way = "down" if other[1] > start[1] else "up"
        check(way not in taken, f"{port_key(dst_port)} runs {way} along the wire from the joint")

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
        self.check_drawn_shape(dst_port, clicks, from_output)
        check(
            self.model.objects.wires.branch(dst_port) is None,
            "a wire from a port starts on a wire",
        )
        return f"wire {port_key(start_port)} -> {port_key(end_port)} corners {clicks}"

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
        hit = top._corner_at(QPointF(*pos))
        # A dot of a selected wire is dragged, also close to a corner
        if hit is None or top._handle_at(QPointF(*pos)) is not None:
            raise Skip("another wire's segment or a dot at the corner")
        return top, pos, hit

    def connect_from_corner(self) -> str:
        top, pos, hit = self.retry(self._corner_pos)
        anchor = (top._parent.dst_port, hit)
        corner_point = top._parent.corner_points()[hit]
        src_port = top._parent._src_port
        inputs = self.free_inputs(src_port.width)
        if not inputs:
            raise Skip("no free input")
        dst_port = self.rng.choice(inputs)
        before = self.routes()
        clicks, _ = self._draw(
            lambda: self.click(pos), dst_port, self.rng.randint(0, 2), expect_ok=True
        )
        wires = self.model.objects.wires
        check((src_port, dst_port) in self.connections(), "the branch is not in the circuit")
        self.check_drawn_shape(dst_port, clicks, from_source=True)
        check(
            wires.branch(dst_port) == anchor,
            f"the branch starts at {wires.branch(dst_port)}, not {anchor}",
        )
        check(
            wires.corner_points(dst_port)[0] == corner_point,
            "the branch doesn't start at the clicked corner",
        )
        self.check_across(dst_port)
        after = self.routes()
        changed = [key for key in before if before[key] != after.get(key)]
        check(not changed, f"other wires changed: {changed}")
        return f"branch from {port_key(anchor[0])} corner {hit} -> {port_key(dst_port)}"

    def connect_to_corner(self) -> str:
        """A wire drawn from an input port to a corner of a wire, also of another width"""
        top, pos, hit = self.retry(self._corner_pos)
        anchor = (top.wire_item.dst_port, hit)
        corner_point = top.wire_item.corner_points()[hit]
        src_port = top.wire_item._src_port
        same_width = self.rng.random() < 0.85
        inputs = [p for p in self.free_inputs() if (p.width == src_port.width) == same_width]
        if not inputs:
            raise Skip("no free input")
        dst_port = self.rng.choice(inputs)
        start_pos = self.port_click_pos(dst_port)
        before = self.routes()
        clicks, _ = self._draw(
            lambda: self.click(start_pos), pos, self.rng.randint(0, 2), expect_ok=same_width
        )
        after = self.routes()
        changed = [key for key in before if before[key] != after.get(key)]
        check(not changed, f"other wires changed: {changed}")
        if not same_width:
            check(dst_port.get_driver() is None, "a wire of another width was connected")
            return f"invalid (width) {port_key(dst_port)} -> {port_key(anchor[0])} corner {hit}"
        wires = self.model.objects.wires
        check((src_port, dst_port) in self.connections(), "the branch is not in the circuit")
        check(
            wires.branch(dst_port) == anchor,
            f"the branch starts at {wires.branch(dst_port)}, not {anchor}",
        )
        check(
            wires.corner_points(dst_port)[0] == corner_point,
            "the branch doesn't start at the clicked corner",
        )
        self.check_drawn_shape(dst_port, clicks, from_source=False)
        self.check_across(dst_port)
        return f"branch {port_key(dst_port)} -> {port_key(anchor[0])} corner {hit}"

    def connect_to_segment(self) -> str:
        """A wire drawn from an input port to a straight part of a wire, at a new joint"""
        part, pos = self.retry(self.segment_pos)
        src_port = part.wire_item._src_port
        inputs = self.free_inputs(src_port.width)
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
            if target is None or target[0] is not part.wire_item.dst_port:
                raise Skip("another item at the edge")
            targets.append(target)

        drawn, _ = self._draw(start, pos, self.rng.randint(0, 2), expect_ok=True)
        # The wire on top, at its corner close by or on the segment
        wire, number, point = targets[0]
        wires = self.model.objects.wires
        check((src_port, dst_port) in self.connections(), "the branch is not in the circuit")
        branch = wires.branch(dst_port)
        start_point = wires.corner_points(dst_port)[0]
        if point is None:
            check(branch == (wire, number), f"the branch starts at {branch}, not corner {number}")
        else:
            check(branch is not None and branch[0] is wire, f"the branch starts on {branch}")
            check(
                abs(start_point[0] - pos[0]) <= 1 and abs(start_point[1] - pos[1]) <= 1,
                f"the branch starts at {start_point}, not {pos}",
            )
        after = self.routes()
        changed = [key for key in before if before[key] != after.get(key)]
        check(not changed, f"other wires changed: {changed}")
        self.check_drawn_shape(dst_port, drawn, from_source=False)
        self.check_across(dst_port)
        return f"branch {port_key(dst_port)} -> {port_key(wire)} at {start_point}"

    def connect_invalid(self) -> str:
        """A connection that must fail: to a driven input, another width, or two outputs"""
        outputs = self.outputs()
        if len(outputs) < 2:
            raise Skip("too few outputs")
        src_port = self.rng.choice(outputs)
        kind = self.rng.choice(["driven", "width", "output"])
        if kind == "driven":
            candidates = sorted((d for _, d in self.connections()), key=port_key)
        elif kind == "width":
            candidates = [p for p in self.free_inputs() if p.width != src_port.width]
        else:
            candidates = [p for p in outputs if p is not src_port]
        if not candidates:
            raise Skip("no candidate")
        end_port = self.rng.choice(candidates)
        start_pos = self.port_click_pos(src_port)
        self._draw(lambda: self.click(start_pos), end_port, 0, expect_ok=False)
        return f"invalid ({kind}) {port_key(src_port)} -> {port_key(end_port)}"

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

    def _delete_selected(self, expected: set[Port]) -> None:
        before = self.routes()
        connections = self.connections()
        self.model.objects.delete_selected()
        self.spin()
        removed = {d for _, d in connections - self.connections()}
        check(
            removed == expected,
            f"deleted {sorted(map(port_key, removed))}, expected {sorted(map(port_key, expected))}",
        )
        after = self.routes()
        for key, line in after.items():
            check(before.get(key) == line, f"the wire to {key} changed shape")

    def delete_route(self) -> str:
        self.clear_selection()
        part, pos = self.segment_pos()
        self.click(pos)
        wires = self.model.objects.wires
        expected = set(wires.sinks_through(part._parent.dst_port, part.segment))
        selected = set(self.scene._selected_wires)
        check(
            selected == expected,
            f"click selected {sorted(map(port_key, selected))}, "
            f"expected {sorted(map(port_key, expected))}",
        )
        # Selected from the closest split before the clicked segment
        firsts = wires.selection(part._parent.dst_port, part.segment)
        for dst_port, item in self.wire_items().items():
            first = firsts.get(dst_port)
            shown = [p.is_wire_selected() for p in item._part_items]
            check(
                shown == [first is not None and p.segment >= first for p in item._part_items],
                f"{port_key(dst_port)} shows {shown} selected, from segment {first} expected",
            )
        self._delete_selected(expected)
        return f"delete {port_key(part._parent.dst_port)} segment {part.segment}"

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
        expected = set(self.model.objects.wires.tree(part._parent.dst_port))
        selected = set(self.scene._selected_wires)
        check(
            selected == expected,
            f"{how} selected {sorted(map(port_key, selected))}, "
            f"expected the tree {sorted(map(port_key, expected))}",
        )
        self._delete_selected(expected)
        return f"delete tree of {port_key(part._parent.dst_port)} by {how}"

    def delete_component(self) -> str:
        objects = self.component_objects()
        if not objects:
            raise Skip("no components")
        obj = self.rng.choice(objects)
        component = obj.component
        self.clear_selection()
        obj.setSelected(True)
        self.spin(5)
        expected = {d for s, d in self.connections() if component in (s.parent(), d.parent())}
        # Wires that start on a deleted wire stay, the routes of the others don't change
        before = self.routes()
        connections = self.connections()
        self.model.objects.delete_selected()
        self.spin()
        removed = {d for _, d in connections - self.connections()}
        check(
            removed == expected,
            f"deleting {component.name()} removed {sorted(map(port_key, removed))}, "
            f"expected {sorted(map(port_key, expected))}",
        )
        check(
            component not in self.model.objects.circuit.get_toplevel_components(),
            "the component is still in the circuit",
        )
        after = self.routes()
        for key, line in after.items():
            check(before.get(key) == line, f"the wire to {key} changed shape")
        return f"delete component {component.name()}"

    def drag_segment(self) -> str:
        self.clear_selection()
        part, pos = self.segment_pos()
        self.click(pos)
        item = part._parent
        movable = [
            p for p in item._part_items if p.is_wire_selected() and item.is_movable(p.segment)
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
        dst_port = item.dst_port
        others = {
            key: line
            for key, line in self.routes().items()
            if key not in [port_key(w) for w in self.model.objects.wires.tree(dst_port)]
        }
        delta = self.rng.choice([-60, -30, 30, 60])
        vertical = segment % 2 == 1
        end = self.snap((dot[0] + delta, dot[1]) if vertical else (dot[0], dot[1] + delta))
        old = list(self.model.objects.wires.path(item._src_port, dst_port))
        self.drag(dot, end)
        new = self.model.objects.wires.path(item._src_port, dst_port)
        check(
            new[segment - 1] == round(end[0] if vertical else end[1]),
            f"segment {segment} of {port_key(dst_port)} not moved: {old} -> {new}",
        )
        after = self.routes()
        for key, line in others.items():
            check(after.get(key) == line, f"another tree's wire {key} changed")
        return f"drag {port_key(dst_port)} segment {segment} by {delta}"

    def edit_segment(self) -> str:
        self.clear_selection()
        part, pos = self.segment_pos()
        item = part._parent
        dst_port = item.dst_port
        wires = self.model.objects.wires
        old = list(wires.path(item._src_port, dst_port))
        old_routes = self.routes()
        text = self.rng.choice(["Split segment", "Add joint", "Merge segments", "Automatic route"])
        state = self.context_menu(pos, text)
        check(text in state, f"no {text} in the menu {state}")
        check(
            dst_port in self.scene._selected_wires,
            "the wire is not selected after the right-click",
        )
        new = wires.path(item._src_port, dst_port)
        if not state[text]:
            check(new == old, f"{text} was disabled but the wire changed")
            return f"{text} (disabled) on {port_key(dst_port)}"
        if text == "Split segment":
            check(len(new) == len(old) + 2, f"split: {old} -> {new}")
        elif text == "Add joint":
            check(len(new) == len(old) + 2, f"joint: {old} -> {new}")
            check(self.routes() == old_routes, "a joint changed the shape of a wire")
            # The menu works on the nearest segment, maybe another one through the point
            new_points = wires.corner_points(dst_port)
            check(
                any(abs(x - pos[0]) <= 1 and abs(y - pos[1]) <= 1 for x, y in new_points),
                f"no joint at {pos}: {new_points}",
            )
        elif text == "Merge segments":
            check(len(new) == len(old) - 2, f"merge: {old} -> {new}")
        else:
            check(new == wires.automatic_path(item._src_port, dst_port), "not the automatic route")
        return f"{text} on {port_key(dst_port)} segment {part.segment}"

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
        old_paths = {
            dst: (list(wires.path(src, dst)), src.parent() in moving and dst.parent() in moving)
            for src, dst in wires.connections()
        }
        self.drag(pos, (pos[0] + delta[0], pos[1] + delta[1]))
        after = (obj.pos().x(), obj.pos().y())
        check(after != before, f"{obj.component.name()} didn't move")
        moved = (round(after[0] - before[0]), round(after[1] - before[1]))
        for src, dst in wires.connections():
            old, between = old_paths[dst]
            # The wires between components that move together move with them
            expected = [
                value + (moved[index % 2] if between else 0) for index, value in enumerate(old)
            ]
            check(
                wires.path(src, dst) == expected,
                f"{port_key(dst)}: {old} -> {wires.path(src, dst)}, not {expected}",
            )
        names = "+".join(member.component.name() for member in group)
        return f"move {names} by {delta}"

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

    def save_and_load(self) -> str:
        path = self.out_dir / "fuzz.circuit"
        before = self.snapshot()
        self.model.save_circuit(path)
        self.model.load_circuit(path)
        self.spin(50)
        check(self.snapshot() == before, "the loaded circuit differs from the saved one")
        self.history.clear()
        self.future.clear()
        return "save and load"

    def run_simulation(self) -> str:
        before = self.snapshot()
        self.model.model_start()
        self.spin(100)
        items = list(self.wire_items().values())
        if items:
            item = self.rng.choice(items)
            self.click(item.corner_points()[1])
            check(
                not self.model.objects.new_wire.ongoing(),
                "a wire was started while the simulation runs",
            )
        self.model.objects.delete_selected()
        self.model.model_stop()
        self.spin(50)
        check(self.snapshot() == before, "the circuit changed while the simulation ran")
        return "run the simulation"

    ACTIONS: ClassVar[list[tuple[str, int]]] = [
        ("add_component", 4),
        ("connect_ports", 6),
        ("connect_from_corner", 4),
        ("connect_to_corner", 3),
        ("connect_to_segment", 3),
        ("connect_invalid", 1),
        ("draw_and_abort", 1),
        ("delete_route", 3),
        ("delete_tree", 1),
        ("delete_component", 2),
        ("drag_segment", 3),
        ("edit_segment", 3),
        ("move_component", 2),
        ("undo", 3),
        ("redo", 2),
        ("save_and_load", 1),
        ("run_simulation", 1),
    ]
    # These don't change the circuit by themselves, or check undo themselves
    NO_UNDO_CHECK: ClassVar[set[str]] = {"undo", "redo", "save_and_load", "run_simulation"}

    def step(self, number: int) -> None:
        """One random action, and the checks after it"""
        actions = dict(self.ACTIONS)
        # Undo and redo when there is something to undo or redo, redo mostly after an undo
        if not self.history:
            del actions["undo"]
        if self.future:
            actions["redo"] = 5
        else:
            del actions["redo"]
        names, weights = list(actions), list(actions.values())
        # A new circuit starts with a few components
        name = "add_component" if number < 4 else self.rng.choices(names, weights)[0]
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


def main() -> int:
    """Run the fuzzer"""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--seed", type=int, default=None, help="random seed (default: random)")
    parser.add_argument("--steps", type=int, default=300, help="number of actions")
    parser.add_argument("-v", "--verbose", action="store_true", help="print every action")
    parser.add_argument("--out", type=Path, default=None, help="folder for saved circuits")
    args = parser.parse_args()
    # Without a window on the screen (set before the QApplication is created)
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    seed = args.seed if args.seed is not None else random.randrange(1_000_000)
    out_dir = args.out or Path(tempfile.mkdtemp(prefix="gui_fuzz_"))
    out_dir.mkdir(parents=True, exist_ok=True)
    fuzzer = GuiFuzzer(seed, args.verbose, out_dir)
    start = time.perf_counter()
    number = 0
    try:
        for number in range(args.steps):
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
    counts = " ".join(f"{name}={count}" for name, count in sorted(fuzzer.counts.items()))
    elapsed = time.perf_counter() - start
    components = len(fuzzer.component_objects())
    wires = len(fuzzer.wire_items())
    print(
        f"gui_fuzz OK seed={seed} steps={args.steps} ({elapsed:.0f} s), "
        f"end: {components} components {wires} wires. {counts}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
