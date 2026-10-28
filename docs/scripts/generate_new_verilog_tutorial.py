# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""
Generate the screenshots for the guide to a new Verilog component (docs/new-verilog.md).

The script follows the guide in the real application window, offscreen: it adds a Yosys
component with a new Verilog file, writes a half adder in the editor, synthesizes it,
connects two switches and two LEDs, and runs the circuit.

Run from the repository root:

    uv run python docs/scripts/generate_new_verilog_tutorial.py
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Callable
from pathlib import Path


os.environ["QT_QPA_PLATFORM"] = "offscreen"
# Settings of their own, not the recent files of the user
os.environ.setdefault("DIGSIM_SETTINGS_DIR", tempfile.mkdtemp(prefix="digsim_settings_"))

import platformdirs

from PySide6.QtCore import QEventLoop, QPoint, QPointF, QRect, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QCommandLinkButton,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QWidget,
)

from digsim.app.editor import VerilogEditor
from digsim.app.gui import MainWindow
from digsim.app.gui._circuit_area import CircuitArea
from digsim.app.gui._component_selection import SelectableComponentWidget
from digsim.app.gui_objects import ComponentObject
from digsim.app.gui_objects._component_port_item import PortGraphicsItem
from digsim.app.model import AppModel
from digsim.app.settings._component_settings import ComponentSettingsDialog


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "images" / "new_verilog"

WINDOW_SIZE = (1100, 680)
EDITOR_SIZE = (860, 560)
HIGHLIGHT_COLOR = QColor(255, 140, 0)

# The design of the guide, as it is typed in the editor
HALF_ADDER = """module half_adder (
    input a,
    input b,
    output sum,
    output carry
);
    assign sum = a ^ b;
    assign carry = a & b;
endmodule
"""


def spin(ms: int) -> None:
    """Let the application run (events, repaints and the simulation thread) for 'ms'"""
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def save(pixmap: QPixmap, name: str, highlights: list[QRect] | None = None) -> None:
    """Save a screenshot, with frames around the parts the guide step is about"""
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(HIGHLIGHT_COLOR)
    pen.setWidth(4)
    painter.setPen(pen)
    for rect in highlights or []:
        painter.drawRoundedRect(rect.adjusted(-5, -5, 5, 5), 7, 7)
    painter.end()
    pixmap.save(str(OUT / f"{name}.png"))


def rect_in(window: QWidget, widget: QWidget) -> QRect:
    """The rectangle of a widget in window coordinates"""
    return QRect(widget.mapTo(window, QPoint(0, 0)), widget.size())


def menu_rect(window: QMainWindow, title: str) -> QRect:
    """The title of a menu in the menu bar, like File, in window coordinates"""
    bar = window.menuBar()
    action = next(a for a in bar.actions() if a.text().replace("&", "") == title)
    rect = bar.actionGeometry(action)
    return QRect(bar.mapTo(window, rect.topLeft()), rect.size())


def handle_dialogs(handlers: list[Callable[[QWidget], None]]) -> None:
    """Call each handler with the next modal dialog that opens, in order"""
    handled: list[QWidget] = []

    def poll() -> None:
        dialog = QApplication.activeModalWidget()
        if dialog is not None and dialog not in handled:
            handled.append(dialog)
            spin(200)
            handlers.pop(0)(dialog)
        if handlers:
            QTimer.singleShot(100, poll)

    QTimer.singleShot(100, poll)


class Guide:
    """The application window, and helpers to operate it like a user"""

    def __init__(self) -> None:
        self.model = AppModel()
        self.window = MainWindow(self.model, "docs")
        self.window.resize(*WINDOW_SIZE)
        self.window.show()
        area = self.window.findChild(CircuitArea)
        assert area is not None
        self.area = area
        area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        spin(300)

    def shot(self, name: str, highlights: list[QRect] | None = None) -> None:
        spin(200)
        save(self.window.grab(), name, highlights)

    def selector_item(self, name: str) -> SelectableComponentWidget:
        for widget in self.window.findChildren(SelectableComponentWidget):
            if widget._name == name:
                scroll_area = self.window.findChild(QScrollArea)
                assert scroll_area is not None
                scroll_area.ensureWidgetVisible(widget)
                spin(100)
                return widget
        raise ValueError(name)

    def button(self, text: str) -> QPushButton:
        for button in self.window.findChildren(QPushButton):
            if button.text() == text:
                return button
        raise ValueError(text)

    def press(self, text: str) -> None:
        QTest.mouseClick(self.button(text), Qt.MouseButton.LeftButton)
        spin(300)

    def add(self, name: str, scene_pos: QPointF) -> ComponentObject:
        """Add a component centered at a position of the scene, as a drop does"""
        before = set(self.model.objects.get_list())
        self.area.add_component(name, scene_pos)
        spin(300)
        (added,) = set(self.model.objects.get_list()) - before
        return added

    def object_rect(self, component_object: ComponentObject) -> QRect:
        """The component's rectangle in window coordinates"""
        view_rect = self.area.mapFromScene(component_object.sceneBoundingRect()).boundingRect()
        return view_rect.translated(self.area.viewport().mapTo(self.window, QPoint(0, 0)))

    def port_item(self, component_object: ComponentObject, name: str) -> PortGraphicsItem:
        for item in component_object.childItems():
            if isinstance(item, PortGraphicsItem) and item._port.name() == name:
                return item
        raise ValueError(name)

    def port_scene_pos(self, component_object: ComponentObject, name: str) -> QPointF:
        return self.port_item(component_object, name).sceneBoundingRect().center()

    def click_port(self, component_object: ComponentObject, name: str) -> None:
        pos = self.area.mapFromScene(self.port_scene_pos(component_object, name))
        QTest.mouseClick(self.area.viewport(), Qt.MouseButton.LeftButton, pos=pos)
        spin(100)

    def click(self, component_object: ComponentObject) -> None:
        pos = self.area.mapFromScene(component_object.sceneBoundingRect().center())
        QTest.mouseClick(self.area.viewport(), Qt.MouseButton.LeftButton, pos=pos)
        spin(500)

    def click_empty(self) -> None:
        """Click the circuit area away from the circuit, so that nothing is selected"""
        pos = self.area.viewport().rect().bottomLeft() + QPoint(20, -20)
        QTest.mouseClick(self.area.viewport(), Qt.MouseButton.LeftButton, pos=pos)
        spin(100)

    def component(self, name: str) -> ComponentObject:
        for component_object in self.model.objects.get_list():
            if component_object.component.name() == name:
                return component_object
        raise ValueError(name)


def wait_for_build(editor: VerilogEditor) -> None:
    while editor.is_building():
        spin(50)
    spin(300)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication([])
    assert app is not None
    # A folder Yosys can read (YoWASP has a private /tmp) for the new Verilog file
    cache_dir = Path(platformdirs.user_cache_dir("digsim", appauthor=False))
    cache_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=cache_dir, ignore_cleanup_errors=True) as work:
        verilog = Path(work) / "half_adder.v"
        # The name from the save dialog, which can't be operated offscreen
        ComponentSettingsDialog._new_verilog_path = staticmethod(lambda parent: str(verilog))
        make_screenshots(Guide())
    print(f"Screenshots written to {OUT.relative_to(ROOT)}")


def make_screenshots(guide: Guide) -> None:
    window = guide.window
    # A new circuit
    guide.shot("01_new_circuit", [menu_rect(window, "File")])

    # Add a Yosys component: open a file or a new Verilog file, then its settings
    yosys_item = guide.selector_item("YosysComponent")

    def open_or_new(dialog: QWidget) -> None:
        (new_button,) = [
            button
            for button in dialog.findChildren(QCommandLinkButton)
            if button.text() == "New Verilog file"
        ]
        save(dialog.grab(), "02_open_or_new", [rect_in(dialog, new_button)])
        new_button.click()

    handle_dialogs([open_or_new])
    center = guide.area.mapToScene(guide.area.viewport().rect().center())
    yosys = guide.add("YosysComponent", center)
    spin(500)
    # It is selected, its settings are in the settings pane
    save(window.settings_dock.grab(), "03_settings")
    (editor,) = window.verilog_editors.editors()
    editor.resize(*EDITOR_SIZE)
    spin(300)
    guide.shot("04_component", [rect_in(window, yosys_item), guide.object_rect(yosys)])
    save(editor.grab(), "05_editor")

    # The half adder
    code = editor.code
    code.selectAll()
    code.insertPlainText(HALF_ADDER)
    spin(200)
    save(editor.grab(), "06_half_adder")

    # Synthesize: the ports change, OK
    def ports_change(dialog: QWidget) -> None:
        save(dialog.grab(), "07_ports_change")
        assert isinstance(dialog, QMessageBox)
        ok = dialog.button(QMessageBox.StandardButton.Ok)
        assert ok is not None
        ok.click()

    handle_dialogs([ports_change])
    editor.synthesize()
    wait_for_build(editor)
    save(editor.grab(), "08_synthesized", [rect_in(editor, editor.build_panel.steps)])
    editor.close()
    spin(300)
    yosys = guide.component("half_adder")
    guide.shot("09_new_ports", [guide.object_rect(yosys)])

    # Two switches, one above and one below the inputs, as they don't fit side by side
    switches = {}
    for port, dy in (("a", -40), ("b", 40)):
        pos = guide.port_scene_pos(yosys, port)
        switches[port] = guide.add("OnOffSwitch", QPointF(pos.x() - 160, pos.y() + dy))

    # Two LEDs: green for the sum, red for the carry, the color in the settings pane. The
    # input of an LED is 10 pixels below its middle.
    leds = {}
    for port, led_color, dy in (("sum", "green", -40), ("carry", "red", 40)):
        pos = guide.port_scene_pos(yosys, port)
        leds[port] = guide.add("Led", QPointF(pos.x() + 140, pos.y() + dy - 10))
        (combo,) = window.settings_pane.findChildren(QComboBox)
        combo.setCurrentText(led_color)
        window.settings_pane.accept()
        spin(200)
    guide.click_empty()
    guide.shot(
        "10_parts", [guide.object_rect(item) for item in [*switches.values(), *leds.values()]]
    )

    # The wires
    for port, switch in switches.items():
        guide.click_port(switch, "O")
        guide.click_port(yosys, port)
    for port, led in leds.items():
        guide.click_port(yosys, port)
        guide.click_port(led, "I")
    QTest.mouseMove(guide.area.viewport(), guide.area.viewport().rect().bottomLeft())
    guide.shot("11_wires")

    # Run it: a on, then b on as well
    guide.press("Start Simulation")
    spin(500)
    guide.click(switches["a"])
    guide.shot("12_a_on", [guide.object_rect(leds["sum"]), guide.object_rect(leds["carry"])])
    guide.click(switches["b"])
    guide.shot("13_both_on", [guide.object_rect(leds["sum"]), guide.object_rect(leds["carry"])])
    guide.press("Stop Simulation")
    guide.model.model_stop()
    guide.model._changed = False


if __name__ == "__main__":
    main()
