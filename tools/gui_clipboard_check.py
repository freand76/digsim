# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""
Checks of copy, cut, paste and duplicate in the GUI. They need Qt's GUI libraries, which
CI doesn't have, so they are not in tests/. Run them offscreen with:

    uv run --with pytest pytest tools/gui_clipboard_check.py
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest


# Without a window on the screen (set before the QApplication is created)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEventLoop, QPointF, Qt, QTimer
from PySide6.QtGui import QAction
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel

from digsim.app.gui import MainWindow
from digsim.app.gui._circuit_area import CircuitArea, WirePartGraphicsItem
from digsim.app.gui._menu_bar import MenuBar
from digsim.app.model import AppModel


EXAMPLES = Path(__file__).parent.parent / "examples"


def spin(ms: int = 20) -> None:
    """Let Qt handle events for a while"""
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


class Gui:
    """The main window, and its Edit menu"""

    def __init__(self) -> None:
        self.app = QApplication.instance() or QApplication([])
        QApplication.clipboard().clear()
        self.model = AppModel()
        self.window = MainWindow(self.model, "check")
        self.window.show()
        area = self.window.findChild(CircuitArea)
        assert area is not None
        self.area = area
        menu_bar = self.window.menuBar()
        assert isinstance(menu_bar, MenuBar)
        self.menu_bar = menu_bar
        spin()

    def add(self, name: str, x: float, y: float, **settings: Any) -> Any:
        component_object = self.model.objects.components.add_object_by_name(
            name, QPointF(x, y), settings
        )
        assert component_object is not None
        self.area.scene().add_scene_component(component_object, True)
        spin()
        return component_object.component

    def select(self, *components: Any) -> None:
        self.area.scene().clearSelection()
        for component in components:
            self.model.objects.components.get_object(component).setSelected(True)
        spin()

    def action(self, text: str) -> QAction:
        """An action of the Edit menu, by its text without & and the shortcut"""
        (edit,) = [a for a in self.menu_bar.actions() if a.text() == "&Edit"]
        for action in edit.menu().actions():
            if action.text().replace("&", "") == text:
                return action
        raise KeyError(text)

    def trigger(self, text: str) -> None:
        action = self.action(text)
        assert action.isEnabled(), text
        action.trigger()
        spin()

    def names(self) -> list[str]:
        return sorted(
            component_object.component.name()
            for component_object in self.model.objects.components.get_object_list()
        )

    def position(self, name: str) -> tuple[int, int]:
        component = self.model.objects.circuit.get_component(name)
        position = self.model.objects.components.get_object(component).to_gui_dataclass()
        return position.x, position.y

    def close(self) -> None:
        self.model.model_stop()
        # Not "are you sure" about the changed circuit
        self.model._changed = False
        self.window.close()
        spin()
        # Not a queued signal to a window that Python is taking apart at exit
        self.window.deleteLater()
        spin()
        # Qt crashes at exit with data of its own on the clipboard
        QApplication.clipboard().clear()
        spin()


@pytest.fixture(name="gui")
def fixture_gui():
    gui = Gui()
    yield gui
    gui.close()


@pytest.fixture(name="wired")
def fixture_wired(gui):
    """A button that drives a LED, and a LED that isn't copied on the same line"""
    button = gui.add("PushButton", 100, 100)
    led = gui.add("Led", 300, 100)
    other = gui.add("Led", 300, 200)
    wires = gui.model.objects.wires
    wires.connect_ports(button.O, led.I)
    wires.connect_ports(button.O, other.I)
    gui.model.sig_update_wires.emit()
    spin()
    return button, led, other


def test_copy_and_paste(gui, wired):
    """The pasted components get new names, and only the lines between them"""
    button, led, other = wired
    assert not gui.action("Paste").isEnabled()
    gui.select(button, led)
    gui.trigger("Copy")
    assert gui.action("Paste").isEnabled()
    gui.trigger("Paste")
    assert gui.names() == ["Led", "Led_1", "Led_2", "PushButton", "PushButton_1"]
    circuit = gui.model.objects.circuit
    new_button = circuit.get_component("PushButton_1")
    new_led = circuit.get_component("Led_2")
    assert new_led.I in new_button.O.wired_ports
    assert other.I not in new_button.O.wired_ports
    assert new_led.I not in button.O.wired_ports
    # A step down and to the right, and the pasted components are selected
    assert gui.position("PushButton_1") == (gui.position("PushButton")[0] + 20, 120)
    selected = sorted(obj.component.name() for obj in gui.area.selected_objects())
    assert selected == ["Led_2", "PushButton_1"]
    # A pasted wire is drawn, and works
    assert any(wire == (new_button.O, new_led.I) for wire in gui.model.objects.wires.drawn())
    new_button.push()
    gui.model.objects.circuit.run(ms=1)
    assert new_led.I.value == 1


def test_paste_is_one_undo_step(gui, wired):
    button, led, _ = wired
    gui.select(button, led)
    gui.trigger("Copy")
    gui.trigger("Paste")
    gui.trigger("Paste")
    assert len(gui.names()) == 7
    # The second paste is a step further
    assert gui.position("PushButton_2") == (gui.position("PushButton")[0] + 40, 140)
    gui.trigger("Undo")
    assert len(gui.names()) == 5
    gui.trigger("Undo")
    assert gui.names() == ["Led", "Led_1", "PushButton"]


def test_cut_and_paste(gui, wired):
    """Cut deletes the components, a paste brings them back"""
    button, led, _ = wired
    gui.select(button, led)
    gui.trigger("Cut")
    assert gui.names() == ["Led_1"]
    gui.trigger("Paste")
    assert gui.names() == ["Led", "Led_1", "PushButton"]


def test_duplicate(gui, wired):
    """Duplicate doesn't change the clipboard"""
    button, _, _ = wired
    gui.select(button)
    gui.trigger("Duplicate")
    assert "PushButton_1" in gui.names()
    assert not gui.action("Paste").isEnabled()


def test_paste_in_another_circuit(gui, tmp_path):
    """A component with a file is pasted in a circuit in another folder"""
    counter = gui.add(
        "YosysComponent", 100, 100, path=str(EXAMPLES / "yosys_counter" / "counter.v")
    )
    gui.select(counter)
    gui.trigger("Copy")
    gui.model.save_circuit(tmp_path / "a.circuit")
    gui.menu_bar.new_circuit()
    spin()
    gui.trigger("Paste")
    assert len(gui.names()) == 1
    text = QApplication.clipboard().text()
    assert str(EXAMPLES / "yosys_counter" / "counter.v") in text


def test_other_text_is_not_pasted(gui):
    QApplication.clipboard().setText("just some text")
    spin()
    assert not gui.action("Paste").isEnabled()
    gui.area.paste()
    assert gui.names() == []


def test_a_wire_alone_is_not_copied(gui, wired):
    """
    With only a wire selected, Copy, Cut and Duplicate are off, Ctrl+C says why, and the
    clipboard keeps what was copied before
    """
    button, led, other = wired
    gui.select(other)
    gui.trigger("Copy")
    copied = QApplication.clipboard().text()
    gui.area.scene().clearSelection()
    (item,) = [
        part
        for part in gui.area.scene().items()
        if isinstance(part, WirePartGraphicsItem) and part.wire_item.wire == (button.O, led.I)
    ][:1]
    item.setSelected(True)
    spin()
    for text in ("Cut", "Copy", "Duplicate"):
        assert not gui.action(text).isEnabled()
    QTest.keyClick(gui.window, Qt.Key.Key_C, Qt.KeyboardModifier.ControlModifier)
    spin()
    message = gui.area.findChild(QLabel)
    assert message is not None and message.isVisible()
    assert message.text().startswith("Nothing to copy")
    assert QApplication.clipboard().text() == copied
    gui.trigger("Paste")
    assert gui.names() == ["Led", "Led_1", "Led_1_1", "PushButton"]


def test_no_message_with_components(gui, wired):
    """With components selected, Ctrl+C copies them, without the message"""
    button, _, _ = wired
    gui.select(button)
    QTest.keyClick(gui.window, Qt.Key.Key_C, Qt.KeyboardModifier.ControlModifier)
    spin()
    message = gui.area.findChild(QLabel)
    assert message is None or not message.isVisible()
    assert "PushButton" in QApplication.clipboard().text()
