# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""
Checks of probes in the GUI: adding one on a wire from its context menu. They need Qt's GUI libraries, which CI doesn't have, so they are not
in tests/. Run them offscreen with:

    uv run --with pytest pytest tools/gui_probe_check.py
"""

from __future__ import annotations

import os
import tempfile
from itertools import pairwise
from typing import Any

import pytest


# Without a window on the screen (set before the QApplication is created)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
# Settings of their own, not the recent files of the user
os.environ.setdefault("DIGSIM_SETTINGS_DIR", tempfile.mkdtemp(prefix="digsim_settings_"))

from PySide6.QtCore import QEventLoop, QPointF, QTimer
from PySide6.QtGui import QContextMenuEvent
from PySide6.QtWidgets import QApplication, QMenu

from digsim.app.gui import MainWindow
from digsim.app.gui._circuit_area import CircuitArea
from digsim.app.model import AppModel
from digsim.app.model._model_components import PROBE_OFFSET
from digsim.circuit.components import HexDigit, Probe, StaticValue


def spin(ms: int = 20) -> None:
    """Let Qt handle events for a while"""
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


class Gui:
    """The main window, and the context menu of its circuit area"""

    def __init__(self) -> None:
        self.app = QApplication.instance() or QApplication([])
        self.model = AppModel()
        self.errors: list[str] = []
        self.model.sig_error.connect(self.errors.append)
        self.window = MainWindow(self.model, "check")
        self.window.resize(1200, 800)
        self.window.show()
        area = self.window.findChild(CircuitArea)
        assert area is not None
        self.area = area
        spin()

    def add(self, name: str, x: float, y: float, **settings: Any) -> Any:
        component_object = self.model.objects.components.add_object_by_name(
            name, QPointF(x, y), settings
        )
        assert component_object is not None, self.errors
        self.area.scene().add_scene_component(component_object, True)
        spin()
        return component_object.component

    def close(self) -> None:
        self.model.model_stop()
        # Not "are you sure" about the changed circuit
        self.model._changed = False
        self.window.close()
        spin()
        # Not a queued signal to a window that Python is taking apart at exit
        self.window.deleteLater()
        spin()

    def context_menu(self, pos: tuple[float, float], text: str) -> list[str]:
        """Right-click and choose a menu item, return the items"""
        items: list[str] = []

        def pick() -> None:
            menu = QApplication.activePopupWidget()
            if not isinstance(menu, QMenu):
                return
            actions = {action.text(): action for action in menu.actions() if action.text()}
            items.extend(actions)
            if text in actions:
                actions[text].trigger()
            menu.close()

        QTimer.singleShot(50, pick)
        view_pos = self.area.mapFromScene(QPointF(*pos))
        QApplication.sendEvent(
            self.area.viewport(),
            QContextMenuEvent(
                QContextMenuEvent.Reason.Mouse,
                view_pos,
                self.area.viewport().mapToGlobal(view_pos),
            ),
        )
        spin(100)
        return items

    def probes(self) -> list[Probe]:
        return [
            component
            for component in self.model.objects.circuit.get_toplevel_components()
            if isinstance(component, Probe)
        ]

    def probe_wire(self, probe: Probe) -> tuple[Any, Any]:
        wires = self.model.objects.wires
        (wire,) = [wire for wire in wires.drawn() if wire[1] is probe.I]
        return wire

    def offset(self, probe: Probe) -> tuple[float, float]:
        """Where the probe's input is from the point on the wire that it is on"""
        wires = self.model.objects.wires
        wire = self.probe_wire(probe)
        assert wires.branch(wire) is not None
        anchor = wires.start_point(wire)
        port = wires.port_pos(probe.I)
        return port[0] - anchor[0], port[1] - anchor[1]


@pytest.fixture(name="gui")
def fixture_gui():
    gui = Gui()
    yield gui
    gui.close()


@pytest.fixture(name="wire")
def fixture_wire(gui):
    """A wire from a static value of 4 bits (5) to a hex digit, with a step in it"""
    value = gui.add("StaticValue", 100, 100, width=4, value=5)
    digit = gui.add("HexDigit", 400, 200, digits=1, dot=False)
    gui.model.objects.wires.connect_ports(value.O, digit.val)
    gui.model.sig_update_wires.emit()
    spin()
    return value.O, digit.val


def segment_middle(gui: Gui, wire: Any) -> tuple[float, float]:
    """The middle of the longest segment of a wire"""
    points = gui.model.objects.wires.corner_points(wire)
    start, end = max(
        pairwise(points),
        key=lambda pair: abs(pair[1][0] - pair[0][0]) + abs(pair[1][1] - pair[0][1]),
    )
    return (start[0] + end[0]) // 2, (start[1] + end[1]) // 2


def add_probe(gui: Gui, wire: Any) -> Probe:
    assert "Add probe" in gui.context_menu(segment_middle(gui, wire), "Add probe")
    spin()
    (probe,) = gui.probes()
    return probe


def test_add_probe_from_the_context_menu(gui, wire):
    """The probe is on the wire, up and to the right of it, and shows its value"""
    probe = add_probe(gui, wire)
    assert probe.I.width == 4
    assert probe.I in wire[0].wired_ports
    assert gui.offset(probe) == PROBE_OFFSET
    assert probe.text() == "5"
    assert not gui.errors


def test_undo_and_redo_add_probe(gui, wire):
    """Adding a probe is one undo step"""
    add_probe(gui, wire)
    gui.model.objects.undo()
    spin()
    assert gui.probes() == []
    gui.model.objects.redo()
    spin()
    (probe,) = gui.probes()
    assert gui.offset(probe) == PROBE_OFFSET


def test_probe_is_saved_and_loaded(gui, wire, tmp_path):
    """A probe is a component on the wire's line"""
    add_probe(gui, wire)
    gui.model.save_circuit(tmp_path / "probe.circuit")
    gui.model.load_circuit(tmp_path / "probe.circuit")
    spin()
    (probe,) = gui.probes()
    (value,) = [
        c
        for c in gui.model.objects.circuit.get_toplevel_components()
        if isinstance(c, StaticValue)
    ]
    (digit,) = [
        c for c in gui.model.objects.circuit.get_toplevel_components() if isinstance(c, HexDigit)
    ]
    assert probe.I in value.O.wired_ports
    assert digit.val in value.O.wired_ports
    assert gui.offset(probe) == PROBE_OFFSET
    assert not gui.errors
