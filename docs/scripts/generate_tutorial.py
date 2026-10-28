# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""
Generate the screenshots for the GUI tutorial (docs/first-circuit.md).

The script builds the tutorial circuit in the real application window, offscreen, with
mouse clicks on ports, components and buttons, and takes a screenshot at each step.

Run from the repository root:

    uv run python docs/scripts/generate_tutorial.py
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


os.environ["QT_QPA_PLATFORM"] = "offscreen"
# Settings of their own, not the recent files of the user
os.environ.setdefault("DIGSIM_SETTINGS_DIR", tempfile.mkdtemp(prefix="digsim_settings_"))

from PySide6.QtCore import QEventLoop, QPoint, QRect, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap, QPolygon
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPushButton, QScrollArea, QWidget

from digsim.app.gui import MainWindow
from digsim.app.gui._circuit_area import CircuitArea
from digsim.app.gui._component_selection import SelectableComponentWidget
from digsim.app.gui_objects import ComponentObject
from digsim.app.gui_objects._component_port_item import PortGraphicsItem
from digsim.app.model import AppModel


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "images" / "tutorial"

WINDOW_SIZE = (1100, 680)
HIGHLIGHT_COLOR = QColor(255, 140, 0)


def spin(ms: int) -> None:
    """Let the application run (events, repaints and the simulation thread) for 'ms'"""
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


# A mouse pointer with its tip at (0, 0)
POINTER = [(0, 0), (0, 22), (6, 17), (10, 26), (14, 24), (10, 16), (17, 16)]


def save(
    pixmap: QPixmap,
    name: str,
    highlights: list[QRect] | None = None,
    pointer: QPoint | None = None,
) -> None:
    """
    Save a screenshot, with frames around the parts the tutorial step is about, and a
    mouse pointer where the user clicks (screenshots don't include the pointer)
    """
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(HIGHLIGHT_COLOR)
    pen.setWidth(4)
    painter.setPen(pen)
    for rect in highlights or []:
        painter.drawRoundedRect(rect.adjusted(-6, -6, 6, 6), 8, 8)
    if pointer is not None:
        pen = QPen(Qt.GlobalColor.black)
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(Qt.GlobalColor.white)
        painter.drawPolygon(QPolygon([pointer + QPoint(x, y) for x, y in POINTER]))
    painter.end()
    pixmap.save(str(OUT / f"{name}.png"))


class Tutorial:
    """The application window, and helpers to operate it like a user"""

    def __init__(self) -> None:
        self.model = AppModel()
        self.window = MainWindow(self.model, "docs")
        self.window.resize(*WINDOW_SIZE)
        self.window.show()
        area = self.window.findChild(CircuitArea)
        assert area is not None
        self.area = area
        # The scene grows when components are added, keep the screenshots clean
        area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        spin(300)

    def shot(
        self, name: str, highlights: list[QRect] | None = None, pointer: QPoint | None = None
    ) -> None:
        """A screenshot of the window, 'pointer' is a position in the circuit area"""
        spin(200)
        if pointer is not None:
            pointer = self.area.viewport().mapTo(self.window, pointer)
        save(self.window.grab(), name, highlights, pointer)

    def rect_in_window(self, widget: QWidget) -> QRect:
        return QRect(widget.mapTo(self.window, QPoint(0, 0)), widget.size())

    def menu_rect(self, title: str) -> QRect:
        """The title of a menu in the menu bar, like File, in window coordinates"""
        bar = self.window.menuBar()
        action = next(a for a in bar.actions() if a.text().replace("&", "") == title)
        rect = bar.actionGeometry(action)
        return QRect(bar.mapTo(self.window, rect.topLeft()), rect.size())

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

    def view_pos(self, fx: float, fy: float) -> QPoint:
        """A position in the circuit area, as fractions of its size"""
        viewport = self.area.viewport()
        return QPoint(int(viewport.width() * fx), int(viewport.height() * fy))

    def view_rect_in_window(self, rect: QRect) -> QRect:
        return rect.translated(self.area.viewport().mapTo(self.window, QPoint(0, 0)))

    def add(self, name: str, fx: float, fy: float) -> ComponentObject:
        """Add a component centered at a position in the circuit area, as a drop does"""
        before = set(self.model.objects.get_list())
        self.area.add_component(name, self.area.mapToScene(self.view_pos(fx, fy)))
        spin(100)
        (added,) = set(self.model.objects.get_list()) - before
        return added

    def object_rect(self, component_object: ComponentObject) -> QRect:
        """The component's rectangle in window coordinates"""
        scene_rect = component_object.sceneBoundingRect()
        view_rect = self.area.mapFromScene(scene_rect).boundingRect()
        return self.view_rect_in_window(view_rect)

    def port_view_pos(self, component_object: ComponentObject, port_name: str) -> QPoint:
        for item in component_object.childItems():
            if isinstance(item, PortGraphicsItem) and item._port.name() == port_name:
                return self.area.mapFromScene(item.sceneBoundingRect().center())
        raise ValueError(port_name)

    def click_view(self, pos: QPoint) -> None:
        QTest.mouseClick(self.area.viewport(), Qt.MouseButton.LeftButton, pos=pos)
        spin(100)

    def move_view(self, pos: QPoint) -> None:
        QTest.mouseMove(self.area.viewport(), pos)
        spin(100)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication([])
    assert app is not None
    tutorial = Tutorial()

    # 1. The empty application
    tutorial.shot("01_main_window")

    # 2. Drag a switch into the circuit area (shown with the drag preview)
    switch_item = tutorial.selector_item("OnOffSwitch")
    drop_pos = tutorial.view_pos(0.15, 0.3)
    tutorial.area._show_drag_preview("OnOffSwitch", drop_pos)
    tutorial.shot("02_drag_switch", [tutorial.rect_in_window(switch_item)], drop_pos)
    tutorial.area._remove_drag_preview()

    # 3. Two switches in the circuit area
    switch_a = tutorial.add("OnOffSwitch", 0.15, 0.3)
    switch_b = tutorial.add("OnOffSwitch", 0.15, 0.65)
    tutorial.shot(
        "03_two_switches", [tutorial.object_rect(switch_a), tutorial.object_rect(switch_b)]
    )

    # 4. The AND gate, it is selected: its settings are in the settings pane
    and_item = tutorial.selector_item("AND")
    and_gate = tutorial.add("AND", 0.45, 0.47)
    spin(200)
    save(tutorial.window.settings_dock.grab(), "04_and_settings")
    tutorial.shot(
        "05_and_gate", [tutorial.rect_in_window(and_item), tutorial.object_rect(and_gate)]
    )

    # 5. The LED, red
    led_item = tutorial.selector_item("Led")
    led = tutorial.add("Led", 0.75, 0.47)
    tutorial.shot("06_led", [tutorial.rect_in_window(led_item), tutorial.object_rect(led)])

    # 6. Start a wire on the first switch's output, and move the mouse
    start = tutorial.port_view_pos(switch_a, "O")
    end = tutorial.port_view_pos(and_gate, "A")
    tutorial.click_view(start)
    wire_end = (start + end) / 2 + QPoint(0, 10)
    tutorial.move_view(wire_end)
    start_port = tutorial.view_rect_in_window(QRect(start - QPoint(6, 6), start + QPoint(6, 6)))
    tutorial.shot("07_wire_started", [start_port], wire_end)
    tutorial.click_view(end)

    # 7. The other wires
    tutorial.click_view(tutorial.port_view_pos(switch_b, "O"))
    tutorial.click_view(tutorial.port_view_pos(and_gate, "B"))
    tutorial.click_view(tutorial.port_view_pos(and_gate, "Y"))
    tutorial.click_view(tutorial.port_view_pos(led, "I"))
    tutorial.move_view(tutorial.view_pos(0.5, 0.9))
    tutorial.shot("08_wires")

    # 8. Start the simulation
    start_button = tutorial.button("Start Simulation")
    QTest.mouseClick(start_button, Qt.MouseButton.LeftButton)
    spin(1000)
    tutorial.shot("09_simulation_started", [tutorial.rect_in_window(start_button)])

    # 9. Turn on one switch, then both
    switch_a_pos = tutorial.area.mapFromScene(switch_a.sceneBoundingRect().center())
    tutorial.click_view(switch_a_pos)
    spin(500)
    tutorial.shot("10_one_switch_on", [tutorial.object_rect(led)], switch_a_pos)
    switch_b_pos = tutorial.area.mapFromScene(switch_b.sceneBoundingRect().center())
    tutorial.click_view(switch_b_pos)
    spin(500)
    tutorial.shot("11_both_switches_on", [tutorial.object_rect(led)], switch_b_pos)

    # 10. Stop the simulation and save the circuit
    QTest.mouseClick(tutorial.button("Stop Simulation"), Qt.MouseButton.LeftButton)
    spin(500)
    tutorial.shot("12_save", [tutorial.menu_rect("File")])

    tutorial.model.model_stop()
    print(f"Screenshots written to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
