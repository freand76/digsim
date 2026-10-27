# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""
Checks of the menu bar of the main window. They need Qt's GUI libraries, which CI doesn't
have, so they are not in tests/. Run them offscreen with:

    uv run --with pytest pytest tools/gui_menu_check.py
"""

from __future__ import annotations

import json
import os
from typing import Any

import pytest


# Without a window on the screen (set before the QApplication is created)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEventLoop, QPointF, QTimer
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from digsim.app.gui import MainWindow
from digsim.app.gui._circuit_area import CircuitArea
from digsim.app.gui._menu_bar import MenuBar
from digsim.app.model import AppModel


def spin(ms: int = 20) -> None:
    """Let Qt handle events for a while"""
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


class Gui:
    """The main window, with the file dialogs answered by 'path'"""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.app = QApplication.instance() or QApplication([])
        self.path = ""
        self.dialogs: list[str] = []
        monkeypatch.setattr(QFileDialog, "getSaveFileName", self._file)
        monkeypatch.setattr(QFileDialog, "getOpenFileName", self._file)
        monkeypatch.setattr(QMessageBox, "question", self._yes)
        self.model = AppModel()
        self.window = MainWindow(self.model, "1.2.3")
        self.window.show()
        menu_bar = self.window.menuBar()
        assert isinstance(menu_bar, MenuBar)
        self.menu_bar = menu_bar
        spin()

    def _file(self, *_args: Any, **_kwargs: Any) -> tuple[str, str]:
        self.dialogs.append("file")
        return self.path, ""

    def _yes(self, *_args: Any) -> QMessageBox.StandardButton:
        self.dialogs.append("question")
        return QMessageBox.StandardButton.Yes

    def action(self, menu: str, text: str) -> QAction:
        """An action of a menu, by its text without & and the shortcut shown after a tab"""
        for menu_action in self.menu_bar.actions():
            if menu_action.text().replace("&", "") != menu:
                continue
            submenu = menu_action.menu()
            for action in submenu.actions():
                if action.text().replace("&", "").split("\t")[0] == text:
                    return action
        raise KeyError(f"{menu} > {text}")

    def trigger(self, menu: str, text: str) -> None:
        self.action(menu, text).trigger()
        spin()

    def add(self, name: str, **settings: Any) -> Any:
        component_object = self.model.objects.components.add_object_by_name(
            name, QPointF(100, 100), settings
        )
        assert component_object is not None
        area = self.window.findChild(CircuitArea)
        assert area is not None
        area.scene().add_scene_component(component_object, True)
        spin()
        return component_object

    def close(self) -> None:
        self.model.model_stop()
        # Not "are you sure" about the changed circuit
        self.model._changed = False
        self.window.close()
        spin()
        # Not a queued signal to a window that Python is taking apart at exit
        self.window.deleteLater()
        spin()


@pytest.fixture(name="gui")
def fixture_gui(monkeypatch):
    gui = Gui(monkeypatch)
    yield gui
    gui.close()


def test_menus(gui):
    """The menus and their shortcuts"""
    menus = [action.text().replace("&", "") for action in gui.menu_bar.actions()]
    assert menus == ["File", "Edit", "View", "Simulation", "Help"]
    assert gui.action("File", "Save").shortcut() == QKeySequence("Ctrl+S")
    assert gui.action("File", "Save As...").shortcut() == QKeySequence("Ctrl+Shift+S")
    assert gui.action("Edit", "Undo").shortcut() == QKeySequence("Ctrl+Z")
    assert gui.action("Edit", "Delete").shortcut() == QKeySequence("Del")


def test_save_as_then_save(gui, tmp_path):
    """Save As asks for a file, Save saves in it without asking"""
    gui.add("Led")
    assert gui.action("File", "Save").isEnabled()
    gui.path = str(tmp_path / "first.circuit")
    gui.trigger("File", "Save")
    assert gui.dialogs == ["file"]
    assert gui.model.circuit_path == gui.path
    assert gui.window.windowTitle().endswith(" - first.circuit")
    assert not gui.action("File", "Save").isEnabled()
    gui.add("Led")
    assert gui.window.windowTitle().endswith(" - first.circuit*")
    gui.trigger("File", "Save")
    assert gui.dialogs == ["file"]
    saved = json.loads((tmp_path / "first.circuit").read_text())
    assert len(saved["circuit"]["components"]) == 2
    gui.path = str(tmp_path / "second.circuit")
    gui.trigger("File", "Save As...")
    assert gui.dialogs == ["file", "file"]
    assert (tmp_path / "second.circuit").exists()
    assert gui.window.windowTitle().endswith(" - second.circuit")


def test_open_and_new(gui, tmp_path):
    """Open loads a file (asking first about a changed circuit), New clears it"""
    gui.add("Led")
    gui.path = str(tmp_path / "led.circuit")
    gui.trigger("File", "Save")
    gui.trigger("File", "New")
    assert gui.model.objects.components.is_empty()
    assert gui.model.circuit_path is None
    gui.add("Led")
    gui.trigger("File", "Open...")
    assert gui.dialogs == ["file", "question", "file"]
    assert gui.model.circuit_path == gui.path
    assert len(gui.model.objects.components.get_object_list()) == 1


def test_undo_redo_and_delete(gui):
    """Undo and Redo follow the undo stack, Delete the selection"""
    assert not gui.action("Edit", "Undo").isEnabled()
    led = gui.add("Led")
    assert gui.action("Edit", "Undo").isEnabled()
    assert not gui.action("Edit", "Delete").isEnabled()
    led.setSelected(True)
    spin()
    assert gui.action("Edit", "Delete").isEnabled()
    gui.trigger("Edit", "Delete")
    assert gui.model.objects.components.is_empty()
    gui.trigger("Edit", "Undo")
    assert not gui.model.objects.components.is_empty()
    assert gui.action("Edit", "Redo").isEnabled()
    gui.trigger("Edit", "Redo")
    assert gui.model.objects.components.is_empty()


def test_simulation(gui):
    """Start turns into Stop while the simulation runs, and the file actions are off"""
    gui.add("Clock")
    gui.trigger("Simulation", "Start")
    spin(100)
    assert gui.model.is_running
    assert gui.action("Simulation", "Stop").text().startswith("&Stop")
    assert not gui.action("File", "Open...").isEnabled()
    assert not gui.action("Edit", "Undo").isEnabled()
    gui.trigger("Simulation", "Stop")
    while gui.model.is_running:
        spin()
    spin()
    assert gui.action("File", "Open...").isEnabled()
    assert gui.action("Simulation", "Reset").isEnabled()
    gui.trigger("Simulation", "Reset")
    assert not gui.action("Simulation", "Reset").isEnabled()


def test_zoom_to_fit(gui):
    """The whole circuit fits in the view, and an empty one has no zoom"""
    gui.add("Led")
    component_object = gui.add("Led")
    component_object.moveBy(3000, 2000)
    gui.model.sig_update_wires.emit()
    spin()
    area = gui.window.findChild(CircuitArea)
    gui.trigger("View", "Zoom to Fit")
    visible = area.mapToScene(area.viewport().rect()).boundingRect()
    assert visible.contains(area.circuit_rect())
    assert area.transform().m11() < 1
    gui.trigger("File", "New")
    gui.trigger("View", "Zoom to Fit")
    assert area.transform().m11() == 1
