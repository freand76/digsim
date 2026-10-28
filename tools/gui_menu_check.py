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
import tempfile
from typing import Any

import pytest


# Without a window on the screen (set before the QApplication is created)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
# Settings of their own, not the recent files of the user
os.environ.setdefault("DIGSIM_SETTINGS_DIR", tempfile.mkdtemp(prefix="digsim_settings_"))

from PySide6.QtCore import QEventLoop, QPointF, Qt, QTimer
from PySide6.QtGui import QAction, QImage, QKeySequence
from PySide6.QtWidgets import QApplication, QComboBox, QFileDialog, QMessageBox, QSlider

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
        # The file type chosen in the file dialog
        self.dialog_filter = ""
        self.dialogs: list[str] = []
        monkeypatch.setattr(QFileDialog, "getSaveFileName", self._file)
        monkeypatch.setattr(QFileDialog, "getOpenFileName", self._file)
        monkeypatch.setattr(QMessageBox, "question", self._yes)
        self.errors: list[str] = []
        monkeypatch.setattr(MainWindow, "error_dialog", lambda _, text: self.errors.append(text))
        self.warnings: list[str] = []
        monkeypatch.setattr(
            MainWindow, "warning_log_dialog", lambda _, _title, text: self.warnings.append(text)
        )
        self.model = AppModel()
        self.window = MainWindow(self.model, "1.2.3")
        self.window.show()
        menu_bar = self.window.menuBar()
        assert isinstance(menu_bar, MenuBar)
        self.menu_bar = menu_bar
        spin()

    def _file(self, *_args: Any, **_kwargs: Any) -> tuple[str, str]:
        self.dialogs.append("file")
        return self.path, self.dialog_filter

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
    """Open loads a file in a tab of its own, New clears the circuit"""
    gui.add("Led")
    gui.path = str(tmp_path / "led.circuit")
    gui.trigger("File", "Save")
    gui.trigger("File", "New")
    assert gui.model.objects.components.is_empty()
    assert gui.model.circuit_path is None
    gui.add("Led")
    gui.trigger("File", "Open...")
    # The changed circuit stays, without a question
    assert gui.dialogs == ["file", "file"]
    assert len(gui.window.tabs()) == 2
    opened = gui.window.current_tab().app_model
    assert opened.circuit_path == gui.path
    assert len(opened.objects.components.get_object_list()) == 1


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


def test_rotate(gui, tmp_path):
    """Rotate turns the selected symbols a quarter, an undo step, saved in the file"""
    gate = gui.add("AND")
    led = gui.add("Led")
    assert not gui.action("Edit", "Rotate").isEnabled()
    led.setSelected(True)
    spin()
    # An LED isn't rotated
    assert not gui.action("Edit", "Rotate").isEnabled()
    gate.setSelected(True)
    spin()
    assert gui.action("Edit", "Rotate").isEnabled()
    gui.trigger("Edit", "Rotate")
    assert (gate.rotation_angle, led.rotation_angle) == (90, 0)
    # The output faces down, its port is below the middle of the gate
    center = gate.mapRectToScene(gate.rect()).center()
    output = gate.get_port_item(gate.component.Y).portPos()
    assert abs(output.x() - center.x()) < 1 and output.y() > center.y()
    # Undo builds the objects again
    gui.trigger("Edit", "Undo")
    rotated = [obj.rotation_angle for obj in gui.model.objects.components.get_object_list()]
    assert rotated == [0, 0]
    gui.trigger("Edit", "Redo")
    gui.path = str(tmp_path / "rotated.circuit")
    gui.trigger("File", "Save")
    saved = json.loads((tmp_path / "rotated.circuit").read_text())
    assert saved["gui"]["AND"]["rotation"] == 90
    assert "rotation" not in saved["gui"]["Led"]


def test_flip(gui, tmp_path):
    """Flip mirrors the selected symbols on the screen, saved in the file"""
    mux = gui.add("MUX")
    mux.setSelected(True)
    spin()
    center = mux.mapRectToScene(mux.rect()).center()
    select = mux.get_port_item(mux.component.S).portPos()
    assert select.y() > center.y()
    gui.trigger("Edit", "Flip Vertical")
    # The select input on top, on the left side still
    select = mux.get_port_item(mux.component.S).portPos()
    assert select.y() < center.y() and select.x() < center.x()
    assert (mux.rotation_angle, mux.flipped) == (0, True)
    gui.trigger("Edit", "Flip Horizontal")
    # Facing left: the output on the left side
    output = mux.get_port_item(mux.component.Y).portPos()
    assert output.x() < center.x()
    assert (mux.rotation_angle, mux.flipped) == (180, False)
    gui.trigger("Edit", "Undo")
    (mux,) = gui.model.objects.components.get_object_list()
    assert (mux.rotation_angle, mux.flipped) == (0, True)
    gui.path = str(tmp_path / "flipped.circuit")
    gui.trigger("File", "Save")
    saved = json.loads((tmp_path / "flipped.circuit").read_text())
    assert saved["gui"]["MUX"]["flipped"] is True


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


def test_export_image(gui, tmp_path):
    """The circuit as PNG, twice the size, and as SVG"""
    gui.add("Led")
    assert gui.action("File", "Export Image...").isEnabled()
    gui.path = str(tmp_path / "circuit")
    gui.dialog_filter = "PNG Image (*.png)"
    gui.trigger("File", "Export Image...")
    image = QImage(str(tmp_path / "circuit.png"))
    area = gui.window.findChild(CircuitArea)
    assert image.width() == 2 * (int(area.circuit_rect().width()) + 40)
    gui.path = str(tmp_path / "circuit.svg")
    gui.trigger("File", "Export Image...")
    assert "<svg" in (tmp_path / "circuit.svg").read_text()


def test_export_needs_a_circuit(gui):
    assert not gui.action("File", "Export Image...").isEnabled()


def test_recent_files(gui, tmp_path):
    """A saved or opened circuit is a recent file, a gone one leaves the list"""
    gui.add("Led")
    first, second = tmp_path / "first.circuit", tmp_path / "second.circuit"
    gui.path = str(first)
    gui.trigger("File", "Save")
    gui.path = str(second)
    gui.trigger("File", "Save As...")
    assert gui.menu_bar.recent_files()[:2] == [str(second), str(first)]
    gui.menu_bar.open_recent(str(first))
    spin()
    assert gui.window.current_tab().app_model.circuit_path == str(first)
    assert gui.menu_bar.recent_files()[0] == str(first)
    second.unlink()
    gui.menu_bar.open_recent(str(second))
    spin()
    assert gui.errors and "gone" in gui.errors[0]
    assert str(second) not in gui.menu_bar.recent_files()


def test_step_clock(gui):
    """Each Step Clock is one rising edge of the clock: the counter counts one"""
    assert not gui.action("Simulation", "Step Clock").isEnabled()
    clock = gui.add("Clock").component
    counter = gui.add("Counter", width=4).component
    gui.model.objects.wires.connect_ports(clock.O, counter.clk)
    gui.model.model_init()
    spin()
    assert gui.action("Simulation", "Step Clock").isEnabled()
    for count in (1, 2, 3):
        gui.trigger("Simulation", "Step Clock")
        while gui.model.is_running:
            spin()
        spin()
        assert counter.Q.value == count
        assert clock.O.value == 1


def test_switch_settles_while_stopped(gui):
    """A switch clicked while the simulation is stopped: the circuit shows the change"""
    switch_object = gui.add("OnOffSwitch")
    switch = switch_object.component
    inverter = gui.add("NOT").component
    led = gui.add("Led").component
    wires = gui.model.objects.wires
    wires.connect_ports(switch.O, inverter.A)
    wires.connect_ports(inverter.Y, led.I)
    gui.model.model_init()
    spin()
    switch_object.single_click_action()
    spin()
    assert (switch.O.value, led.I.value) == (1, 0)
    # From the context menu too
    switch_object._toggle()
    spin()
    assert (switch.O.value, led.I.value) == (0, 1)
    assert not gui.model.is_running


def test_reset_clears_the_logic_analyzer(gui):
    """Reset starts over at time 0, without the samples of the last run"""
    switch_object = gui.add("OnOffSwitch")
    analyzer = gui.add("LogicAnalyzer").component
    gui.model.objects.wires.connect_ports(switch_object.component.O, analyzer.A)
    gui.model.model_init()
    switch_object.single_click_action()
    gui.trigger("Simulation", "Start")
    spin(300)
    gui.trigger("Simulation", "Stop")
    while gui.model.is_running:
        spin()
    assert 1 in analyzer.signal_data()["A"]
    gui.trigger("Simulation", "Reset")
    assert analyzer.signal_data()["A"] == [0] * 100


def test_tabs(gui, tmp_path):
    """Files open in tabs of their own, once, and only the shown tab simulates"""
    window = gui.window
    gui.add("Clock")
    gui.path = str(tmp_path / "clock.circuit")
    gui.trigger("File", "Save")
    gui.trigger("File", "New Tab")
    assert len(window.tabs()) == 2
    assert window.current_tab().title() == "Untitled"
    # The new tab is unused: the file opens in it, and the second time its tab is shown
    other = tmp_path / "other.circuit"
    other.write_text((tmp_path / "clock.circuit").read_text())
    window.open_file(str(other))
    assert len(window.tabs()) == 2
    assert window.current_tab().title() == "other.circuit"
    window.open_file(gui.path)
    assert window.current_tab() is window.tabs()[0]
    # Switching tabs stops the simulation of the tab that is left
    gui.trigger("Simulation", "Start")
    spin(100)
    assert gui.model.is_running
    window.open_file(str(other))
    while gui.model.is_running:
        spin()
    assert gui.menu_bar._app_model is window.current_tab().app_model
    gui.trigger("File", "Close Tab")
    assert len(window.tabs()) == 1


def test_subcircuit_view(gui):
    """A view of a subcircuit shows its parts, and the simulation goes on in it"""
    from pathlib import Path

    window = gui.window
    path = Path(__file__).parent.parent / "example_circuits" / "full_adder.circuit"
    gui.model.load_circuit(str(path))
    spin()
    gui.model.sig_view_subcircuit.emit("half_adder")
    spin()
    (view,) = window.view_tabs()
    assert view.subcircuit is gui.model.objects.circuit.get_component("half_adder")
    # The editing actions are off in a view
    assert not gui.action("Edit", "Undo").isEnabled()
    # Viewing it again shows the tab, switching to it doesn't stop the simulation
    window._tabs.setCurrentIndex(0)
    gui.model.model_start()
    spin(100)
    gui.model.sig_view_subcircuit.emit("half_adder")
    spin(100)
    assert len(window.view_tabs()) == 1
    assert gui.model.is_running
    gui.model.model_stop()
    # Closing the circuit's tab closes its views
    gui.model._changed = False
    window._tabs.setCurrentIndex(0)
    gui.trigger("File", "Close Tab")
    assert window.view_tabs() == []


def _pane_input(gui: Gui, widget_type: Any, number: int = 0) -> Any:
    """An input of the settings pane, like its first slider"""
    return gui.window.settings_pane.findChildren(widget_type)[number]


def _apply(gui: Gui) -> None:
    gui.window.settings_pane._apply_button.click()
    spin()


def test_settings_pane_follows_the_selection(gui):
    pane = gui.window.settings_pane
    led = gui.add("Led")
    gate = gui.add("AND")
    assert pane._title.text() == "Settings"
    led.setSelected(True)
    spin()
    assert pane._title.text() == "Led"
    # Two components: none of them
    gate.setSelected(True)
    spin()
    assert pane._title.text() == "Settings"
    led.setSelected(False)
    spin()
    assert pane._title.text() == "AND"


def test_settings_pane_reconfigures_in_place(gui):
    """A setting that can be reconfigured changes the component, it stays where it is"""
    led = gui.add("Led")
    led.setSelected(True)
    spin()
    color = _pane_input(gui, QComboBox)
    color.setCurrentIndex(color.findData("green"))
    _apply(gui)
    assert led.component.color == "green"
    assert gui.model.objects.components.get_object(led.component) is led
    gui.trigger("Edit", "Undo")
    (component,) = gui.model.objects.circuit.get_toplevel_components()
    assert component.color == "red"


def test_settings_pane_builds_the_component_again(gui):
    """More inputs on a gate: built again, with its wires, an undo step"""
    switches = [gui.add("OnOffSwitch") for _ in range(2)]
    gate = gui.add("AND")
    led = gui.add("Led")
    wires = gui.model.objects.wires
    wires.connect_ports(switches[0].component.O, gate.component.A)
    wires.connect_ports(switches[1].component.O, gate.component.B)
    wires.connect_ports(gate.component.Y, led.component.I)
    gui.model.sig_update_wires.emit()
    spin()
    gate.setSelected(True)
    spin()
    _pane_input(gui, QSlider).setValue(3)
    _apply(gui)
    new_gate = gui.model.objects.circuit.get_component("AND")
    assert [port.name() for port in new_gate.inports()] == ["A", "B", "C"]
    assert {driver.parent().name() for driver in new_gate.A.get_drivers()} == {"OnOffSwitch"}
    assert new_gate.Y.wired_ports == [gui.model.objects.circuit.get_component("Led").I]
    # Still selected, the pane shows it
    assert gui.window.settings_pane._title.text() == "AND"
    assert not gui.warnings
    gui.trigger("Edit", "Undo")
    gate = gui.model.objects.circuit.get_component("AND")
    assert len(gate.inports()) == 2


def test_settings_pane_removes_the_wires_of_a_port_of_another_width(gui):
    value = gui.add("StaticValue")
    led = gui.add("Led")
    gui.model.objects.wires.connect_ports(value.component.O, led.component.I)
    value.setSelected(True)
    spin()
    # The width is the second slider, after the value
    _pane_input(gui, QSlider, 1).setValue(4)
    _apply(gui)
    assert gui.model.objects.circuit.get_component("StaticValue").O.width == 4
    assert gui.model.objects.circuit.get_component("Led").I.get_drivers() == []
    # The line falls apart, one of its ports has the other width
    (warning,) = gui.warnings
    assert "StaticValue.O" in warning or "Led.I" in warning


def test_settings_pane_changes_the_kind_of_flip_flop(gui):
    flip_flop = gui.add("SRFF")
    flip_flop.setSelected(True)
    spin()
    kinds = _pane_input(gui, QComboBox)
    kinds.setCurrentIndex(kinds.findData("ClockedJKFF"))
    _apply(gui)
    (component,) = gui.model.objects.circuit.get_toplevel_components()
    assert type(component).__name__ == "ClockedJKFF"
    assert component.name() == "SRFF"


def test_settings_pane_is_hidden_and_shown(gui):
    action = gui.action("View", "Settings Pane")
    assert action.isChecked()
    gui.trigger("View", "Settings Pane")
    assert not gui.window.settings_dock.isVisible()
    assert MenuBar.settings().value("window/settings_pane", type=bool) is False
    gui.trigger("View", "Settings Pane")
    assert gui.window.settings_dock.isVisible()


def test_added_component_is_selected_without_a_dialog(gui):
    area = gui.window.findChild(CircuitArea)
    area.add_component("Counter", None)
    spin()
    (counter,) = gui.model.objects.components.get_object_list()
    assert counter.isSelected()
    assert gui.window.settings_pane._title.text() == "Counter"


def _hex_editor(gui: Gui, component_object: Any) -> Any:
    from digsim.app.gui._hex_editor import HexEditorDialog

    return HexEditorDialog(gui.window, gui.model, component_object)


def test_hex_editor_saves_the_file(gui, tmp_path):
    """A word changed in the hex editor is saved in the file, and the ROM has it"""
    path = tmp_path / "rom.hex"
    path.write_text("01 02 03\n", encoding="utf-8")
    rom = gui.add("ROM", path=str(path), address_width=4)
    editor = _hex_editor(gui, rom)
    model = editor.model
    assert model.data(model.index(0, 2)) == "03"
    assert model.setData(model.index(0, 5), "a5")
    assert not model.setData(model.index(0, 6), "1ff")
    assert editor.save()
    assert path.read_text(encoding="utf-8").split()[:6] == ["01", "02", "03", "00", "00", "A5"]
    gui.model.objects.circuit.init()
    assert rom.component.read(5) == 0xA5
    editor.close()


def test_hex_editor_asks_for_a_file_for_a_ram(gui, tmp_path):
    ram = gui.add("RAM", address_width=4, data_width=16)
    editor = _hex_editor(gui, ram)
    editor.model.setData(editor.model.index(0, 1), "1234")
    gui.path = str(tmp_path / "ram.bin")
    assert editor.save()
    assert (tmp_path / "ram.bin").read_bytes() == b"\x00\x00\x34\x12"
    (ram,) = gui.model.objects.circuit.get_toplevel_components()
    assert ram.parameter_get("path") == gui.path
    assert gui.action("Edit", "Undo").isEnabled()
    editor.close()


def test_hex_editor_words_before_the_load_address(gui, tmp_path):
    """They are not in the file, they can't be changed"""
    path = tmp_path / "rom.bin"
    path.write_bytes(b"\x07")
    rom = gui.add("ROM", path=str(path), address_width=4, load_address=4)
    model = _hex_editor(gui, rom).model
    assert model.data(model.index(0, 4)) == "07"
    assert not model.flags(model.index(0, 3)) & Qt.ItemFlag.ItemIsEditable
    assert model.flags(model.index(0, 4)) & Qt.ItemFlag.ItemIsEditable


def test_hex_editor_shows_the_ram_in_the_simulation(gui, tmp_path):
    """The words a RAM has now, the written ones marked: saved as a file, or as contents"""
    path = tmp_path / "ram.hex"
    path.write_text("11 22\n", encoding="utf-8")
    ram = gui.add("RAM", path=str(path), address_width=4, mode="async")
    gui.model.objects.circuit.init()
    # As a write in the simulation does
    ram.component._mem[3] = 0x42
    editor = _hex_editor(gui, ram)
    now = editor.now_model
    assert now is not None
    assert [now.data(now.index(0, column)) for column in range(4)] == ["11", "22", "00", "42"]
    assert now.data(now.index(0, 3), Qt.ItemDataRole.BackgroundRole) is not None
    assert now.data(now.index(0, 1), Qt.ItemDataRole.BackgroundRole) is None
    assert not now.flags(now.index(0, 3)) & Qt.ItemFlag.ItemIsEditable
    editor._view.setCurrentIndex(1)
    assert editor.table.model() is now
    # Save As: a file of its own, the RAM's file is as it was
    gui.path = str(tmp_path / "dump.bin")
    assert editor.save_simulation_as()
    assert (tmp_path / "dump.bin").read_bytes() == b"\x11\x22\x00\x42"
    assert path.read_text(encoding="utf-8") == "11 22\n"
    # Use as Contents, then Save: the file has the word
    editor.use_simulation()
    assert editor.table.model() is editor.model
    assert editor.model.changed
    assert editor.save()
    assert path.read_text(encoding="utf-8").split()[:4] == ["11", "22", "00", "42"]
    editor.close()


def test_hex_editor_of_a_rom_has_no_simulation_view(gui, tmp_path):
    path = tmp_path / "rom.hex"
    path.write_text("01\n", encoding="utf-8")
    rom = gui.add("ROM", path=str(path), address_width=4)
    assert _hex_editor(gui, rom).now_model is None
