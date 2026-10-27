# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""
Checks of the component search of the GUI. They need Qt's GUI libraries, which CI
doesn't have, so they are not in tests/. Run them offscreen with:

    uv run --with pytest pytest tools/gui_search_check.py
"""

from __future__ import annotations

import os
import tempfile

import pytest


# Without a window on the screen (set before the QApplication is created)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
# Settings of their own, not the recent files of the user
os.environ.setdefault("DIGSIM_SETTINGS_DIR", tempfile.mkdtemp(prefix="digsim_settings_"))

from PySide6.QtCore import QEventLoop, Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLineEdit, QListWidget

import digsim.app.gui._component_search as component_search
from digsim.app.gui import MainWindow
from digsim.app.gui._circuit_area import CircuitArea
from digsim.app.model import AppModel
from digsim.app.settings import ComponentSettingsDialog


def spin(ms: int = 20) -> None:
    """Let Qt handle events for a while"""
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


class Gui:
    """The main window, with the settings dialog of a new component accepted at once"""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.app = QApplication.instance() or QApplication([])
        monkeypatch.setattr(
            ComponentSettingsDialog, "start", classmethod(lambda *_args: (True, {}))
        )
        self.dragged: list[str] = []
        monkeypatch.setattr(
            component_search,
            "start_component_drag",
            lambda _source, name: self.dragged.append(name),
        )
        self.model = AppModel()
        self.window = MainWindow(self.model, "check")
        self.window.show()
        self.window.activateWindow()
        area = self.window.findChild(CircuitArea)
        assert area is not None
        self.area = area
        search = self.window.findChild(component_search.ComponentSearch)
        assert search is not None
        self.field = search.findChild(QLineEdit)
        results = self.window.findChild(component_search._ResultList)
        assert results is not None
        self.results: QListWidget = results
        spin()

    def open_search(self) -> None:
        """Ctrl+K"""
        QTest.keyClick(self.window, Qt.Key.Key_K, Qt.KeyboardModifier.ControlModifier)
        spin()

    def type(self, text: str) -> None:
        QTest.keyClicks(self.field, text)
        spin()

    def shown(self) -> list[str]:
        """The names of the results, if they are shown"""
        if not self.results.isVisible():
            return []
        return [self.results.item(row).text() for row in range(self.results.count())]

    def components(self) -> list[str]:
        return [
            type(component_object.component).__name__
            for component_object in self.model.objects.components.get_object_list()
        ]

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


def test_shortcut_focuses_the_search(gui):
    """Ctrl+K and Ctrl+F bring the search to the front, its text selected"""
    gui.area.setFocus()
    gui.open_search()
    assert QApplication.focusWidget() is gui.field
    gui.type("led")
    gui.area.setFocus()
    spin()
    QTest.keyClick(gui.window, Qt.Key.Key_F, Qt.KeyboardModifier.ControlModifier)
    spin()
    assert QApplication.focusWidget() is gui.field
    assert gui.field.selectedText() == "led"


def test_results_follow_the_text(gui):
    """The matches, the best first, are shown while there is text"""
    gui.open_search()
    assert gui.shown() == []
    gui.type("led")
    assert gui.shown()[:2] == ["Led", "LED bar"]
    gui.field.clear()
    spin()
    assert gui.shown() == []


def test_enter_adds_the_best_match(gui):
    """Enter adds the first result, and the search is done"""
    gui.open_search()
    gui.type("prb")
    QTest.keyClick(gui.field, Qt.Key.Key_Return)
    spin(50)
    assert gui.components() == ["Probe"]
    assert gui.field.text() == ""
    assert gui.shown() == []


def test_arrow_keys_choose_another(gui):
    """Down moves to the next result, Enter adds that one"""
    gui.open_search()
    gui.type("led")
    QTest.keyClick(gui.field, Qt.Key.Key_Down)
    QTest.keyClick(gui.field, Qt.Key.Key_Return)
    spin(50)
    assert gui.components() == ["LedBar"]


def test_drag_a_result(gui):
    """A result is dragged like a component of the component selection"""
    gui.open_search()
    gui.type("and")
    gui.results.startDrag(Qt.DropAction.CopyAction)
    spin()
    assert gui.dragged == ["AND"]
    assert gui.shown() == []


def test_escape_clears_the_search(gui):
    """Esc clears the search, and the circuit area gets the focus"""
    gui.open_search()
    gui.type("mux")
    QTest.keyClick(gui.field, Qt.Key.Key_Escape)
    spin()
    assert gui.field.text() == ""
    assert gui.shown() == []
    assert QApplication.focusWidget() is gui.area


def test_results_close_when_the_focus_leaves(gui):
    """Clicking elsewhere closes the results, the text stays"""
    gui.open_search()
    gui.type("ram")
    assert gui.shown()
    gui.area.setFocus()
    spin()
    assert gui.shown() == []
    assert gui.field.text() == "ram"


def test_not_while_running(gui):
    """While the simulation runs, components can't be added: no search"""
    gui.model.model_start()
    spin(100)
    gui.open_search()
    assert QApplication.focusWidget() is not gui.field
    gui.model.model_stop()
    while gui.model.is_running:
        spin()
