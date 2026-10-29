# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""
Generate the screenshots for the Verilog editor tutorial (docs/verilog-tutorial.md).

The script loads a copy of circuits/yosys_counter/counter_yosys_verilog.circuit (and of the
counter.v next to it) in the real application window, offscreen, and follows the tutorial:
it runs the counter, opens the Verilog editor from the context menu, formats and changes
the Verilog, synthesizes it, and runs the counter again.

Run from the repository root:

    uv run python docs/scripts/generate_verilog_tutorial.py
"""

from __future__ import annotations

import os
import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path


os.environ["QT_QPA_PLATFORM"] = "offscreen"
# Settings of their own, not the recent files of the user
os.environ.setdefault("DIGSIM_SETTINGS_DIR", tempfile.mkdtemp(prefix="digsim_settings_"))

import platformdirs

from PySide6.QtCore import QEvent, QEventLoop, QPoint, QRect, Qt, QTimer
from PySide6.QtGui import QColor, QContextMenuEvent, QMouseEvent, QPainter, QPen, QPixmap
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMenu, QPushButton, QWidget

from digsim.app.editor import VerilogEditor
from digsim.app.gui import MainWindow
from digsim.app.gui._circuit_area import CircuitArea
from digsim.app.gui_objects import ComponentObject
from digsim.app.model import AppModel


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "images" / "verilog_tutorial"

WINDOW_SIZE = (1148, 680)
EDITOR_SIZE = (860, 600)
HIGHLIGHT_COLOR = QColor(255, 140, 0)


def spin(ms: int) -> None:
    """Let the application run (events, repaints and the simulation thread) for 'ms'"""
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def save(pixmap: QPixmap, name: str, highlights: list[QRect] | None = None) -> None:
    """Save a screenshot, with frames around the parts the tutorial step is about"""
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(HIGHLIGHT_COLOR)
    pen.setWidth(4)
    painter.setPen(pen)
    for rect in highlights or []:
        painter.drawRoundedRect(rect.adjusted(-4, -4, 4, 4), 6, 6)
    painter.end()
    pixmap.save(str(OUT / f"{name}.png"))


def rect_in(window: QWidget, widget: QWidget, rect: QRect | None = None) -> QRect:
    """A rectangle of a widget (all of it by default) in window coordinates"""
    rect = rect if rect is not None else widget.rect()
    return QRect(widget.mapTo(window, rect.topLeft()), rect.size())


def with_popup(window: QWidget, menu: QMenu, highlight: str) -> tuple[QPixmap, QRect]:
    """A screenshot of a window with a menu over it, and the rectangle of a menu item"""
    pixmap = window.grab()
    offset = menu.mapToGlobal(QPoint(0, 0)) - window.mapToGlobal(QPoint(0, 0))
    painter = QPainter(pixmap)
    painter.drawPixmap(offset, menu.grab())
    painter.end()
    (action,) = [action for action in menu.actions() if action.text() == highlight]
    return pixmap, menu.actionGeometry(action).translated(offset)


class Tutorial:
    """The application window, and helpers to operate it like a user"""

    def __init__(self, circuit: Path) -> None:
        self.model = AppModel()
        self.window = MainWindow(self.model, "docs")
        self.window.resize(*WINDOW_SIZE)
        self.window.show()
        area = self.window.findChild(CircuitArea)
        assert area is not None
        self.area = area
        spin(300)
        self.model.load_circuit(circuit)
        spin(300)
        # All of the circuit
        self.area.zoom_fit()
        spin(300)

    def component(self, name: str) -> ComponentObject:
        for component_object in self.model.objects.get_list():
            if component_object.component.name() == name:
                return component_object
        raise ValueError(name)

    def object_rect(self, component_object: ComponentObject) -> QRect:
        """The component's rectangle in window coordinates"""
        scene_rect = component_object.sceneBoundingRect()
        view_rect = self.area.mapFromScene(scene_rect).boundingRect()
        return view_rect.translated(self.area.viewport().mapTo(self.window, QPoint(0, 0)))

    def view_pos(self, component_object: ComponentObject) -> QPoint:
        return self.area.mapFromScene(component_object.sceneBoundingRect().center())

    def click(self, component_object: ComponentObject) -> None:
        QTest.mouseClick(
            self.area.viewport(), Qt.MouseButton.LeftButton, pos=self.view_pos(component_object)
        )
        spin(100)

    def button(self, text: str) -> QPushButton:
        for button in self.window.findChildren(QPushButton):
            if button.text() == text:
                return button
        raise ValueError(text)

    def press(self, text: str) -> None:
        QTest.mouseClick(self.button(text), Qt.MouseButton.LeftButton)
        spin(300)

    def shot(self, name: str, highlights: list[QRect] | None = None) -> None:
        spin(200)
        save(self.window.grab(), name, highlights)

    def context_menu(
        self, component_object: ComponentObject, pick: Callable[[QMenu], None]
    ) -> None:
        """Right-click a component, and call 'pick' with the menu when it is open"""

        def on_open() -> None:
            menu = QApplication.activePopupWidget()
            assert isinstance(menu, QMenu)
            spin(100)
            pick(menu)

        QTimer.singleShot(200, on_open)
        viewport = self.area.viewport()
        pos = self.view_pos(component_object)
        right = Qt.MouseButton.RightButton
        for kind in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonRelease):
            buttons = right if kind == QEvent.Type.MouseButtonPress else Qt.MouseButton.NoButton
            event = QMouseEvent(
                kind,
                pos,
                viewport.mapToGlobal(pos),
                right,
                buttons,
                Qt.KeyboardModifier.NoModifier,
            )
            if kind == QEvent.Type.MouseButtonRelease:
                QApplication.sendEvent(
                    viewport,
                    QContextMenuEvent(
                        QContextMenuEvent.Reason.Mouse, pos, viewport.mapToGlobal(pos)
                    ),
                )
            QApplication.sendEvent(viewport, event)
        spin(300)


def editor_shot(editor: VerilogEditor, name: str, highlights: list[QRect] | None = None) -> None:
    spin(200)
    save(editor.grab(), name, highlights)


def line_rect(editor: VerilogEditor, line: int) -> QRect:
    """The rectangle of a line (from 1) of the text, in editor coordinates"""
    code = editor.code
    block = code.document().findBlockByNumber(line - 1)
    geometry = code.blockBoundingGeometry(block).translated(code.contentOffset()).toRect()
    geometry.setLeft(0)
    geometry.setWidth(code.viewport().width())
    return rect_in(editor, code.viewport(), geometry)


def select_text(editor: VerilogEditor, text: str) -> None:
    """Select the first match of a text"""
    cursor = editor.code.document().find(text)
    assert not cursor.isNull(), text
    editor.code.setTextCursor(cursor)


def run_counter(tutorial: Tutorial, until: int) -> None:
    """
    Start the simulation, reset the counter, enable it, and stop the simulation when the
    counter has a value (so that the screenshot shows it)
    """
    tutorial.press("Start Simulation")
    reset = tutorial.component("PushButton_2")
    QTest.mousePress(
        tutorial.area.viewport(), Qt.MouseButton.LeftButton, pos=tutorial.view_pos(reset)
    )
    spin(300)
    QTest.mouseRelease(
        tutorial.area.viewport(), Qt.MouseButton.LeftButton, pos=tutorial.view_pos(reset)
    )
    spin(100)
    switch = tutorial.component("OnOffSwitch")
    if not switch.component.active:
        tutorial.click(switch)
    counter = tutorial.component("counter").component
    for _ in range(1000):
        if counter.cnt.value == until:
            break
        spin(10)
    assert counter.cnt.value == until
    tutorial.press("Stop Simulation")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication([])
    assert app is not None
    # A folder Yosys can read (YoWASP has a private /tmp), with the circuit and the Verilog
    # where the circuit expects it
    cache_dir = Path(platformdirs.user_cache_dir("digsim", appauthor=False))
    cache_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=cache_dir, ignore_cleanup_errors=True) as work:
        work_dir = Path(work)
        folder = work_dir / "yosys_counter"
        folder.mkdir()
        circuit = folder / "counter_yosys_verilog.circuit"
        for name in (circuit.name, "counter.v"):
            shutil.copy(ROOT / "circuits" / "yosys_counter" / name, folder / name)
        make_screenshots(Tutorial(circuit))
    print(f"Screenshots written to {OUT.relative_to(ROOT)}")


def make_screenshots(tutorial: Tutorial) -> None:
    window = tutorial.window
    counter = tutorial.component("counter")
    hex_digit = tutorial.component("HexDigit_4")

    # 1. The example circuit
    tutorial.shot("01_circuit", [tutorial.object_rect(counter)])

    # 2. It counts by one
    run_counter(tutorial, until=7)
    tutorial.shot("02_counting", [tutorial.object_rect(hex_digit)])

    # 3. The context menu of the counter
    def edit(menu: QMenu) -> None:
        pixmap, rect = with_popup(window, menu, "Edit Verilog...")
        save(pixmap, "03_context_menu", [rect])
        (action,) = [action for action in menu.actions() if action.text() == "Edit Verilog..."]
        menu.close()
        action.trigger()

    tutorial.context_menu(counter, edit)
    spin(300)
    (editor,) = window.verilog_editors.editors()
    editor.resize(*EDITOR_SIZE)
    spin(300)

    # 4. The editor
    editor_shot(editor, "04_editor")

    # 5. The Build menu, and the formatted Verilog
    build_menu = editor.menuBar().actions()[2].menu()
    assert isinstance(build_menu, QMenu)
    build_menu.popup(
        editor.menuBar().mapToGlobal(
            editor.menuBar().actionGeometry(editor.menuBar().actions()[2]).bottomLeft()
        )
    )
    spin(300)
    pixmap, rect = with_popup(editor, build_menu, "&Format")
    save(pixmap, "05_build_menu", [rect])
    build_menu.close()
    editor.menu_actions["format"].trigger()
    editor_shot(editor, "06_formatted")

    # 6. Count by three
    select_text(editor, "cnt + 1")
    cursor = editor.code.textCursor()
    cursor.setPosition(cursor.selectionEnd() - 1)
    cursor.setPosition(cursor.position() + 1, cursor.MoveMode.KeepAnchor)
    editor.code.setTextCursor(cursor)
    QTest.keyClicks(editor.code, "3")
    line = editor.code.textCursor().blockNumber() + 1
    editor_shot(editor, "07_edited", [line_rect(editor, line)])

    # 7. Synthesize
    editor.synthesize()
    while editor.is_building():
        spin(50)
    editor_shot(editor, "08_synthesized", [rect_in(editor, editor.build_panel.steps)])

    # 8. A mistake: a missing semicolon
    select_text(editor, "cnt + 3;")
    cursor = editor.code.textCursor()
    cursor.setPosition(cursor.selectionEnd())
    cursor.deletePreviousChar()
    editor.code.setTextCursor(cursor)
    editor.synthesize()
    while editor.is_building():
        spin(50)
    error_line = next(iter(editor.code.marks()))
    editor_shot(
        editor,
        "09_error",
        [line_rect(editor, error_line), rect_in(editor, editor.build_panel.messages)],
    )
    # Fixed again
    QTest.keyClicks(editor.code, ";")
    editor.synthesize()
    while editor.is_building():
        spin(50)
    spin(200)
    editor.close()
    spin(200)

    # 9. It counts by three
    run_counter(tutorial, until=9)
    tutorial.shot("10_counting_by_three", [tutorial.object_rect(hex_digit)])
    tutorial.model.model_stop()
    tutorial.model._changed = False


if __name__ == "__main__":
    main()
