# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""
Checks of the GUI for Verilog: reloading a Yosys component whose ports changed, and the
Verilog editor. They need Qt's GUI libraries, which CI doesn't have, so they are not in
tests/. Run them offscreen with:

    uv run --with pytest pytest tools/gui_editor_check.py
"""

from __future__ import annotations

import os
import tempfile
from contextlib import nullcontext
from pathlib import Path

import platformdirs
import pytest


# Without a window on the screen (set before the QApplication is created)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
# Settings of their own, not the recent files of the user
os.environ.setdefault("DIGSIM_SETTINGS_DIR", tempfile.mkdtemp(prefix="digsim_settings_"))

from PySide6.QtCore import QEventLoop, QPointF, Qt, QTimer
from PySide6.QtGui import QTextCursor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QInputDialog, QMessageBox

from digsim.app.editor import VerilogEditor
from digsim.app.gui import MainWindow
from digsim.app.gui_objects._component_context_menu import ComponentContextMenu
from digsim.app.model import AppModel
from digsim.circuit.components import YosysComponent


BEFORE = """
module m(input a, input [3:0] b, output y, output [3:0] q);
   assign y = a;
   assign q = b;
endmodule
"""
# y is gone, b is wider, z is new
AFTER = """
module m(input a, input [7:0] b, output z, output [3:0] q);
   assign z = a;
   assign q = b[3:0];
endmodule
"""
# The same ports as BEFORE
SAME_PORTS = """
module m(input a, input [3:0] b, output y, output [3:0] q);
   assign y = ~a;
   assign q = b;
endmodule
"""


def spin(ms: int = 20) -> None:
    """Let Qt handle events for a while"""
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


class Gui:
    """The main window, with the dialogs it would show recorded instead"""

    def __init__(self, monkeypatch: pytest.MonkeyPatch, work_dir: Path) -> None:
        self.app = QApplication.instance() or QApplication([])
        self.work_dir = work_dir
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.questions: list[str] = []
        self.answer = QMessageBox.StandardButton.Ok
        # The answer to questions (QMessageBox.question), the first ones from 'replies'
        self.reply = QMessageBox.StandardButton.Cancel
        self.replies: list[QMessageBox.StandardButton] = []
        monkeypatch.setattr(MainWindow, "error_dialog", lambda _, text: self.errors.append(text))
        monkeypatch.setattr(
            MainWindow,
            "warning_log_dialog",
            lambda _, title, text: self.warnings.append(f"{title}: {text}"),
        )
        monkeypatch.setattr(QMessageBox, "warning", self._question)
        monkeypatch.setattr(QMessageBox, "question", self._reply)
        monkeypatch.setattr(
            QMessageBox, "critical", lambda _parent, _title, text, *_: self.errors.append(text)
        )
        self.model = AppModel()
        self.window = MainWindow(self.model, "check")
        self.window.show()
        spin()

    def _question(self, _parent, _title, text, *_args):
        self.questions.append(text)
        return self.answer

    def _reply(self, _parent, _title, text, *_args):
        self.questions.append(text)
        if self.replies:
            return self.replies.pop(0)
        return self.reply

    def add(self, name: str, x: float, y: float, **settings):
        component_object = self.model.objects.components.add_object_by_name(
            name, QPointF(x, y), settings
        )
        assert component_object is not None, self.errors
        spin()
        return component_object.component

    def close(self) -> None:
        self.model.model_stop()
        # Not "are you sure" about the changed circuit
        self.model._changed = False
        for editor in self.window.verilog_editors.editors():
            editor.code.document().setModified(False)
        self.window.close()
        spin()
        # Not a queued signal to a window that Python is taking apart at exit
        self.window.deleteLater()
        spin()


@pytest.fixture(name="work_dir")
def fixture_work_dir():
    """A folder Yosys can read: YoWASP has a private /tmp"""
    cache_dir = Path(platformdirs.user_cache_dir("digsim", appauthor=False))
    cache_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=cache_dir, ignore_cleanup_errors=True) as work_dir:
        yield Path(work_dir)


@pytest.fixture(name="gui")
def fixture_gui(monkeypatch, work_dir):
    gui = Gui(monkeypatch, work_dir)
    yield gui
    gui.close()


@pytest.fixture(name="circuit")
def fixture_circuit(gui):
    """A button to m.a, a static value to m.b, and m.y to a LED"""
    path = gui.work_dir / "m.v"
    path.write_text(BEFORE, encoding="utf-8")
    button = gui.add("PushButton", 0, 0)
    value = gui.add("StaticValue", 0, 200, width=4, value=5)
    m = gui.add("YosysComponent", 300, 0, path=str(path))
    led = gui.add("Led", 600, 0)
    wires = gui.model.objects.wires
    wires.connect_ports(button.O, m.a)
    wires.connect_ports(value.O, m.b)
    wires.connect_ports(m.y, led.I)
    gui.model.sig_synchronize_gui.emit()
    spin()
    return path


def yosys(gui: Gui) -> YosysComponent:
    (component,) = [
        component
        for component in gui.model.objects.circuit.get_toplevel_components()
        if isinstance(component, YosysComponent)
    ]
    return component


def yosys_component(gui: Gui, name: str) -> YosysComponent:
    (component,) = [
        component
        for component in gui.model.objects.circuit.get_toplevel_components()
        if isinstance(component, YosysComponent) and component.name() == name
    ]
    return component


def reload_component(gui: Gui, name: str) -> None:
    component_object = gui.model.objects.components.get_object(yosys_component(gui, name))
    component_object._reload(gui.window)
    spin()


def reload(gui: Gui) -> None:
    component_object = gui.model.objects.components.get_object(yosys(gui))
    component_object._reload(gui.window)
    spin()


def connections(gui: Gui) -> list[str]:
    return sorted(
        f"{src.parent().name()}.{src.name()}>{dst.parent().name()}.{dst.name()}"
        for src, dst in gui.model.objects.wires.connections()
    )


def test_reload_with_changed_ports(gui, circuit):
    assert connections(gui) == ["PushButton.O>m.a", "StaticValue.O>m.b", "m.y>Led.I"]
    circuit.write_text(AFTER, encoding="utf-8")
    reload(gui)
    assert gui.errors == [] and gui.warnings == []
    (question,) = gui.questions
    assert "Port 'y' is removed" in question
    assert "Port 'b' has 8 bits instead of 4" in question
    assert "Port 'z' is new" in question
    assert " - m.b\n" in question and " - m.y\n" in question
    component = yosys(gui)
    assert set(component.interface()) == {"a", "b", "z", "q"}
    # The GUI object is new, with items for the new ports
    component_object = gui.model.objects.components.get_object(component)
    for port in component.ports:
        assert component_object.get_port_item(port) is not None
    assert connections(gui) == ["PushButton.O>m.a"]
    assert not gui.model.objects.can_undo()
    # The ports are drawn where the wires are
    wires = gui.model.objects.wires
    (wire,) = wires.drawn()
    assert wires.corner_points(wire)[-1] == wires.port_pos(component.a)


def test_reload_cancelled(gui, circuit):
    circuit.write_text(AFTER, encoding="utf-8")
    gui.answer = QMessageBox.StandardButton.Cancel
    reload(gui)
    assert len(gui.questions) == 1
    assert set(yosys(gui).interface()) == {"a", "b", "y", "q"}
    assert connections(gui) == ["PushButton.O>m.a", "StaticValue.O>m.b", "m.y>Led.I"]


def test_reload_with_the_same_ports(gui, circuit):
    circuit.write_text(SAME_PORTS, encoding="utf-8")
    undo_steps = len(gui.model.objects._undo_stack)
    reload(gui)
    assert gui.questions == [] and gui.errors == [] and gui.warnings == []
    assert connections(gui) == ["PushButton.O>m.a", "StaticValue.O>m.b", "m.y>Led.I"]
    assert len(gui.model.objects._undo_stack) == undo_steps + 1


def test_reload_with_an_error(gui, circuit):
    circuit.write_text("module m(input a; endmodule\n", encoding="utf-8")
    reload(gui)
    (warning,) = gui.warnings
    assert warning.startswith("Reload Yosys Warning")
    assert connections(gui) == ["PushButton.O>m.a", "StaticValue.O>m.b", "m.y>Led.I"]


def test_reload_while_running(gui, circuit):
    gui.model.model_start()
    spin(100)
    assert gui.model.is_running
    circuit.write_text(AFTER, encoding="utf-8")
    reload(gui)
    assert not gui.model.is_running
    assert connections(gui) == ["PushButton.O>m.a"]


# The Verilog editor


def open_editor(gui: Gui, path: Path) -> VerilogEditor:
    gui.model.sig_edit_verilog.emit(str(path))
    spin()
    (editor,) = gui.window.verilog_editors.editors()
    return editor


def set_cursor(editor: VerilogEditor, line: int, column: int, select_to=None) -> None:
    """Put the cursor at a line and column (from 0), selecting to another (line, column)"""
    document = editor.code.document()
    cursor = QTextCursor(document)
    cursor.setPosition(document.findBlockByNumber(line).position() + column)
    if select_to is not None:
        to_line, to_column = select_to
        position = document.findBlockByNumber(to_line).position() + to_column
        cursor.setPosition(position, QTextCursor.MoveMode.KeepAnchor)
    editor.code.setTextCursor(cursor)


def test_context_menu_opens_the_editor(gui, circuit):
    component_object = gui.model.objects.components.get_object(yosys(gui))
    menu = ComponentContextMenu(gui.window, gui.model, component_object)
    (action,) = [action for action in menu.actions() if action.text() == "Edit Verilog..."]
    action.trigger()
    spin()
    (editor,) = gui.window.verilog_editors.editors()
    assert editor.path == circuit.resolve()
    assert editor.code.toPlainText() == BEFORE
    assert not editor.is_modified()
    assert editor.windowTitle() == "m.v[*] - Verilog Editor"
    # The same file opens the same editor
    gui.model.sig_edit_verilog.emit(str(circuit))
    spin()
    assert gui.window.verilog_editors.editors() == [editor]


def test_no_edit_for_a_netlist(gui, work_dir):
    path = work_dir / "m.json"
    (work_dir / "m.v").write_text(BEFORE, encoding="utf-8")
    import json

    path.write_text(json.dumps(YosysComponent.synthesize_file(work_dir / "m.v")), encoding="utf-8")
    component = gui.add("YosysComponent", 0, 0, path=str(path))
    component_object = gui.model.objects.components.get_object(component)
    menu = ComponentContextMenu(gui.window, gui.model, component_object)
    texts = [action.text() for action in menu.actions()]
    assert "Reload" in texts
    assert "Edit Verilog..." not in texts


def test_edit_and_save(gui, work_dir):
    path = work_dir / "crlf.v"
    path.write_bytes(b"module m;\r\nendmodule\r\n")
    editor = open_editor(gui, path)
    assert editor.code.toPlainText() == "module m;\nendmodule\n"
    set_cursor(editor, 0, len("module m;"))
    QTest.keyClick(editor.code, Qt.Key.Key_Return)
    QTest.keyClicks(editor.code, "wire a;")
    assert editor.is_modified()
    assert editor.isWindowModified()
    assert editor.save()
    assert not editor.is_modified()
    # The newlines of the file are kept
    assert path.read_bytes() == b"module m;\r\n    wire a;\r\nendmodule\r\n"


def test_tab_and_indent(gui, work_dir):
    path = work_dir / "t.v"
    path.write_text("a;\nb;\nc;\n", encoding="utf-8")
    editor = open_editor(gui, path)
    set_cursor(editor, 0, 1)
    QTest.keyClick(editor.code, Qt.Key.Key_Tab)
    assert editor.code.toPlainText().startswith("a   ;")
    editor.code.undo()
    # Two lines selected, to the start of the third
    set_cursor(editor, 0, 0, select_to=(2, 0))
    QTest.keyClick(editor.code, Qt.Key.Key_Tab)
    assert editor.code.toPlainText() == "    a;\n    b;\nc;\n"
    QTest.keyClick(editor.code, Qt.Key.Key_Backtab)
    assert editor.code.toPlainText() == "a;\nb;\nc;\n"
    editor.menu_actions["comment"].trigger()
    assert editor.code.toPlainText() == "// a;\n// b;\nc;\n"
    editor.menu_actions["comment"].trigger()
    assert editor.code.toPlainText() == "a;\nb;\nc;\n"


def test_enter_indents_after_begin(gui, work_dir):
    path = work_dir / "t.v"
    path.write_text("  always @(posedge clk) begin\n", encoding="utf-8")
    editor = open_editor(gui, path)
    set_cursor(editor, 0, len("  always @(posedge clk) begin"))
    QTest.keyClick(editor.code, Qt.Key.Key_Return)
    QTest.keyClicks(editor.code, "x")
    assert editor.code.toPlainText() == "  always @(posedge clk) begin\n      x\n"
    # One undo step for the new line
    editor.code.undo()
    editor.code.undo()
    assert editor.code.toPlainText() == "  always @(posedge clk) begin\n"


def test_find_and_replace(gui, circuit):
    editor = open_editor(gui, circuit)
    bar = editor.find_bar
    bar.open_bar(replace=True)
    bar.set_text("assign", "ASSIGN")
    assert bar.find_next()
    assert editor.code.textCursor().selectedText() == "assign"
    assert bar.replace_all() == 2
    assert editor.code.toPlainText() == BEFORE.replace("assign", "ASSIGN")
    # Replace all is one undo step
    editor.code.undo()
    assert editor.code.toPlainText() == BEFORE
    bar.set_text("nothing like this")
    assert not bar.find_next()


def test_go_to_line_and_marks(gui, circuit, monkeypatch):
    editor = open_editor(gui, circuit)
    monkeypatch.setattr(QInputDialog, "getInt", lambda *args: (3, True))
    editor.menu_actions["go_to_line"].trigger()
    assert editor.code.textCursor().blockNumber() == 2
    editor.code.set_marks({3: ("error", "syntax error")})
    assert editor.code.marks() == {3: ("error", "syntax error")}
    assert any(
        selection.format.underlineStyle() != 0 for selection in editor.code.extraSelections()
    )
    QTest.keyClicks(editor.code, "x")
    assert editor.code.marks() == {}


def test_highlighting(gui, circuit):
    editor = open_editor(gui, circuit)
    spin()
    block = editor.code.document().findBlockByNumber(1)
    assert block.text().startswith("module")
    formats = block.layout().formats()
    assert any(f.start == 0 and f.length == len("module") for f in formats)


def test_revert(gui, circuit):
    editor = open_editor(gui, circuit)
    QTest.keyClicks(editor.code, "junk")
    gui.reply = QMessageBox.StandardButton.Cancel
    editor.menu_actions["revert"].trigger()
    assert editor.is_modified()
    gui.reply = QMessageBox.StandardButton.Discard
    editor.menu_actions["revert"].trigger()
    assert not editor.is_modified()
    assert editor.code.toPlainText() == BEFORE


def test_changed_on_disk(gui, circuit):
    editor = open_editor(gui, circuit)
    circuit.write_text(SAME_PORTS, encoding="utf-8")
    for _ in range(50):
        spin(20)
        if editor.code.toPlainText() == SAME_PORTS:
            break
    assert editor.code.toPlainText() == SAME_PORTS
    # With changes in the editor, it asks
    QTest.keyClicks(editor.code, "junk")
    gui.reply = QMessageBox.StandardButton.No
    circuit.write_text(AFTER, encoding="utf-8")
    for _ in range(50):
        spin(20)
        if gui.questions:
            break
    assert "changed by another program" in gui.questions[-1]
    assert editor.code.toPlainText().startswith("junk")
    # Saving our own changes doesn't ask
    editor.save()
    spin(200)
    assert len(gui.questions) == 1


def test_close_with_changes(gui, circuit):
    editor = open_editor(gui, circuit)
    QTest.keyClicks(editor.code, "junk")
    gui.reply = QMessageBox.StandardButton.Cancel
    assert not editor.close()
    # The main window doesn't close either
    gui.model._changed = False
    assert not gui.window.close()
    assert gui.window.isVisible()
    gui.reply = QMessageBox.StandardButton.Discard
    assert editor.close()
    spin()
    assert gui.window.verilog_editors.editors() == []
    assert circuit.read_text(encoding="utf-8") == BEFORE


def test_close_saves(gui, circuit):
    editor = open_editor(gui, circuit)
    QTest.keyClicks(editor.code, "// x")
    QTest.keyClick(editor.code, Qt.Key.Key_Return)
    # Save, and don't update the components
    gui.replies = [QMessageBox.StandardButton.Save, QMessageBox.StandardButton.No]
    assert editor.close()
    assert circuit.read_text(encoding="utf-8").startswith("// x\n")
    assert "not updated with the saved file" in gui.questions[1]


# Synthesis in the editor


def build(editor: VerilogEditor) -> list[tuple[str, str]]:
    """Synthesize, wait until it is done, and return the steps (symbol, name)"""
    editor.menu_actions["synthesize"].trigger()
    for _ in range(1500):
        if not editor.is_building():
            break
        spin(20)
    assert not editor.is_building()
    spin()
    return editor.build_panel.step_status()


def test_synthesize_with_the_same_ports(gui, circuit):
    editor = open_editor(gui, circuit)
    editor.code.setPlainText(SAME_PORTS)
    assert build(editor) == [
        ("✓", "Save"),
        ("✓", "List modules"),
        ("✓", "Synthesize into gates"),
        ("✓", "Check ports"),
        ("✓", "Update components"),
    ]
    assert not editor.is_modified()
    assert circuit.read_text(encoding="utf-8") == SAME_PORTS
    assert gui.questions == [] and gui.errors == [] and gui.warnings == []
    assert connections(gui) == ["PushButton.O>m.a", "StaticValue.O>m.b", "m.y>Led.I"]
    assert gui.model.objects.can_undo()
    # The new Verilog is simulated: y = ~a
    gui.model.model_single_step()
    for _ in range(50):
        spin(20)
        if not gui.model.is_running:
            break
    assert yosys(gui).y.value == 1


def test_synthesize_with_changed_ports(gui, circuit):
    editor = open_editor(gui, circuit)
    editor.code.setPlainText(AFTER)
    assert build(editor) == [
        ("✓", "Save"),
        ("✓", "List modules"),
        ("✓", "Synthesize into gates"),
        ("⚠", "Check ports"),
        ("✓", "Update components"),
    ]
    (question,) = gui.questions
    assert "Port 'y' is removed" in question
    assert connections(gui) == ["PushButton.O>m.a"]
    assert not gui.model.objects.can_undo()
    steps = editor.build_panel.steps
    detail = steps.topLevelItem(3).text(3)
    assert "Port 'y' is removed" in detail and "2 wires removed" in detail


def test_synthesize_cancelled(gui, circuit):
    editor = open_editor(gui, circuit)
    editor.code.setPlainText(AFTER)
    gui.answer = QMessageBox.StandardButton.Cancel
    assert build(editor)[-1] == ("–", "Update components")
    assert set(yosys(gui).interface()) == {"a", "b", "y", "q"}
    # The file is saved
    assert circuit.read_text(encoding="utf-8") == AFTER


def test_synthesize_with_an_error(gui, circuit):
    editor = open_editor(gui, circuit)
    editor.code.setPlainText(BEFORE.replace("assign y = a;", "assign y = a &;"))
    assert build(editor) == [("✓", "Save"), ("✗", "List modules")]
    assert editor.code.marks().keys() == {3}
    kind, text = editor.code.marks()[3]
    assert kind == "error" and "syntax error" in text
    messages = editor.build_panel.messages
    item = messages.topLevelItem(0)
    assert item.text(1) == "3"
    assert editor.build_panel.tabs.tabText(0) == "Messages (1)"
    editor.code.go_to_line(1)
    messages.itemActivated.emit(item, 0)
    assert editor.code.textCursor().blockNumber() == 2
    # The Yosys log, and its filter
    assert "ERROR" in editor.build_panel.log.toPlainText()
    editor.build_panel.log_filter.setText("syntax error")
    assert all("syntax error" in line for line in editor.build_panel.log.toPlainText().split("\n"))
    # The component is as it was
    assert connections(gui) == ["PushButton.O>m.a", "StaticValue.O>m.b", "m.y>Led.I"]


def test_synthesize_with_warnings(gui, circuit):
    editor = open_editor(gui, circuit)
    editor.code.setPlainText(SAME_PORTS.replace("assign y = ~a;", "assign y = ~undeclared;"))
    steps = build(editor)
    assert steps[2] == ("⚠", "Synthesize into gates")
    assert steps[-1] == ("✓", "Update components")
    assert editor.code.marks()[3][0] == "warning"


def test_synthesize_without_components(gui, work_dir):
    path = work_dir / "alone.v"
    path.write_text(BEFORE, encoding="utf-8")
    editor = open_editor(gui, path)
    assert build(editor) == [
        ("✓", "Save"),
        ("✓", "List modules"),
        ("✓", "Synthesize into gates"),
        ("–", "Update components"),
    ]


def test_synthesize_two_components(gui, circuit):
    """Both components of the file are updated, synthesized as they are"""
    gui.add("YosysComponent", 300, 300, path=str(circuit), functional=True)
    editor = open_editor(gui, circuit)
    editor.code.setPlainText(AFTER)
    steps = build(editor)
    assert ("✓", "Synthesize into gates") in steps
    assert ("✓", "Synthesize into functional blocks") in steps
    assert steps[-1] == ("✓", "Update components")
    components = gui.model.objects.components.yosys_components(str(circuit))
    assert len(components) == 2
    assert all(set(component.interface()) == {"a", "b", "z", "q"} for component in components)


def test_synthesize_while_running(gui, circuit):
    gui.model.model_start()
    spin(100)
    editor = open_editor(gui, circuit)
    editor.code.setPlainText(AFTER)
    assert build(editor)[-1] == ("✓", "Update components")
    assert not gui.model.is_running


def test_port_change_with_vcd(gui, circuit, work_dir):
    """The VCD file starts over with the new ports, and the simulation writes them"""
    vcd = work_dir / "waves.vcd"
    gui.model.objects.circuit.vcd(str(vcd))
    gui.model.model_init()
    gui.model.model_start()
    spin(100)
    editor = open_editor(gui, circuit)
    editor.code.setPlainText(AFTER)
    assert build(editor)[-1] == ("✓", "Update components")
    assert not gui.model.is_running
    gui.model.model_start()
    spin(100)
    gui.model.model_stop()
    gui.model.objects.circuit.vcd_close()
    text = vcd.read_text()
    header = text[: text.index("$enddefinitions")]
    assert " z " in header and " y " not in header
    assert "#0" in text


def test_close_while_synthesizing(gui, circuit):
    editor = open_editor(gui, circuit)
    editor.code.setPlainText(AFTER)
    editor.menu_actions["synthesize"].trigger()
    assert editor.is_building()
    assert editor.close()
    spin(200)
    # Nothing was updated
    assert set(yosys(gui).interface()) == {"a", "b", "y", "q"}
    assert gui.questions == []


# Format


def test_format(gui, work_dir):
    path = work_dir / "f.v"
    text = "module f(input a, output y);\nassign y = a;  \n\n\nendmodule\n"
    path.write_text(text, encoding="utf-8")
    editor = open_editor(gui, path)
    set_cursor(editor, 1, 3)
    editor.menu_actions["format"].trigger()
    assert editor.code.toPlainText() == (
        "module f(input a, output y);\n    assign y = a;\n\nendmodule\n"
    )
    assert editor.code.textCursor().blockNumber() == 1
    assert editor.code.textCursor().positionInBlock() == 4
    assert editor.is_modified()
    # One undo step
    editor.code.undo()
    assert editor.code.toPlainText() == text


def test_format_error(gui, work_dir, monkeypatch):
    import digsim.verilog._formatter

    path = work_dir / "f.v"
    path.write_text("module f;\nwire a;\nendmodule\n", encoding="utf-8")
    editor = open_editor(gui, path)
    # As if formatting changed the code
    monkeypatch.setattr(digsim.verilog._formatter, "_same_tokens", lambda text: [text])
    assert not editor.format_code()
    assert editor.code.toPlainText() == "module f;\nwire a;\nendmodule\n"
    assert editor.statusBar().currentMessage().startswith("Not formatted")


# A new Verilog file


def add_yosys_from_dialog(
    gui: Gui, monkeypatch, choice: str, path: Path | None, saved_as: str | list | None = None
) -> None:
    """
    Add a Yosys component as the GUI does: 'choice' is the answer to open or new ("open",
    "new" or "" to cancel), and 'path' the file the file dialog gives ('saved_as' is what
    is typed in the save dialog, the path if not given)
    """
    from PySide6.QtWidgets import QCheckBox, QFileDialog

    from digsim.app.gui._circuit_area import CircuitArea
    from digsim.app.settings import ComponentSettingsDialog

    answer = str(path) if path is not None else ""
    monkeypatch.setattr(ComponentSettingsDialog, "_open_or_new", lambda *_: choice)
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *_, **__: (answer, ""))
    # The answers of the save dialog, each time it is shown ("" when they run out)
    saved = list(saved_as) if isinstance(saved_as, list) else [saved_as or answer]
    monkeypatch.setattr(
        QFileDialog,
        "getSaveFileName",
        lambda *_, **__: (saved.pop(0) if saved else "", ""),
    )

    def accept(_dialog):
        raise AssertionError("A Yosys component is added without a settings dialog")

    monkeypatch.setattr(ComponentSettingsDialog, "exec", accept)
    area = gui.window.findChild(CircuitArea)
    area.add_component("YosysComponent", None)
    spin()
    # The settings the settings pane shows for the new component, it is selected
    gui.asked = [box.accessibleName() for box in gui.window.settings_pane.findChildren(QCheckBox)]


def test_new_verilog_file(gui, work_dir, monkeypatch):
    path = work_dir / "my-blinky.v"
    add_yosys_from_dialog(gui, monkeypatch, "new", path)
    assert gui.questions == []
    assert path.read_text(encoding="utf-8").startswith("module my_blinky (")
    component = yosys(gui)
    assert component.name() == "my_blinky"
    assert component.interface() == {"a": ("input", 1), "y": ("output", 1)}
    (editor,) = gui.window.verilog_editors.editors()
    assert editor.path == path.resolve()


def test_new_verilog_file_gets_v(gui, work_dir, monkeypatch):
    """A name without .v gets it"""
    add_yosys_from_dialog(gui, monkeypatch, "new", None, saved_as=str(work_dir / "blinky"))
    assert (work_dir / "blinky.v").exists()
    assert yosys(gui).name() == "blinky"


def test_new_with_the_name_of_a_file(gui, circuit, monkeypatch):
    """A new file with the name of a file that exists: asked, it is used and not changed"""
    gui.reply = QMessageBox.StandardButton.Yes
    add_yosys_from_dialog(gui, monkeypatch, "new", circuit)
    (question,) = gui.questions
    assert "m.v exists already" in question
    assert circuit.read_text(encoding="utf-8") == BEFORE
    assert len(gui.model.objects.components.yosys_components(str(circuit))) == 2
    assert len(gui.window.verilog_editors.editors()) == 1


def test_new_with_the_name_of_a_file_another_name(gui, circuit, work_dir, monkeypatch):
    """No: the save dialog again, for another name"""
    gui.reply = QMessageBox.StandardButton.No
    other = work_dir / "other.v"
    add_yosys_from_dialog(gui, monkeypatch, "new", None, saved_as=[str(circuit), str(other)])
    assert len(gui.questions) == 1
    assert circuit.read_text(encoding="utf-8") == BEFORE
    assert other.read_text(encoding="utf-8").startswith("module other (")


def test_new_with_the_name_of_a_file_cancelled(gui, circuit, monkeypatch):
    """No, and then the save dialog is cancelled: nothing is added"""
    gui.reply = QMessageBox.StandardButton.No
    add_yosys_from_dialog(gui, monkeypatch, "new", None, saved_as=[str(circuit)])
    assert len(gui.model.objects.components.yosys_components(str(circuit))) == 1


def test_new_cancelled(gui, work_dir, monkeypatch):
    add_yosys_from_dialog(gui, monkeypatch, "new", None)
    assert gui.model.objects.circuit.get_toplevel_components() == []
    assert list(work_dir.iterdir()) == []


def test_open_or_new_cancelled(gui, work_dir, monkeypatch):
    add_yosys_from_dialog(gui, monkeypatch, "", work_dir / "never.v")
    assert gui.model.objects.circuit.get_toplevel_components() == []
    assert gui.window.verilog_editors.editors() == []


def test_open_existing_file_opens_no_editor(gui, circuit, monkeypatch):
    add_yosys_from_dialog(gui, monkeypatch, "open", circuit)
    assert len(gui.model.objects.components.yosys_components(str(circuit))) == 2
    assert gui.window.verilog_editors.editors() == []


def test_open_or_new_dialog(gui, monkeypatch):
    """The dialog that asks to open a file or make a new one"""
    from digsim.app.settings._component_settings import OpenOrNewDialog

    exec_dialog = OpenOrNewDialog.exec
    for button, choice in (("open_button", "open"), ("new_button", "new"), (None, "")):

        def click(dialog, button=button):
            def press():
                if button is None:
                    dialog.reject()
                else:
                    getattr(dialog, button).click()

            QTimer.singleShot(0, press)
            return exec_dialog(dialog)

        monkeypatch.setattr(OpenOrNewDialog, "exec", click)
        assert OpenOrNewDialog.ask(gui.window) == choice


# Update the components when the editor closes


def save_text(editor: VerilogEditor, text: str) -> None:
    editor.code.setPlainText(text)
    assert editor.save()


def wait_closed(gui: Gui) -> None:
    """Wait until the editors have closed (and are deleted)"""
    for _ in range(1500):
        if not gui.window.verilog_editors.editors():
            break
        spin(20)
    spin()


def test_close_without_update(gui, circuit):
    editor = open_editor(gui, circuit)
    save_text(editor, SAME_PORTS)
    gui.reply = QMessageBox.StandardButton.No
    assert editor.close()
    (question,) = gui.questions
    assert "m.v are not updated with the saved file" in question
    # The components are as they were: y = a
    assert yosys(gui).interface() == {
        "a": ("input", 1),
        "b": ("input", 4),
        "y": ("output", 1),
        "q": ("output", 4),
    }
    spin()
    assert gui.window.verilog_editors.editors() == []


def test_close_cancelled(gui, circuit):
    editor = open_editor(gui, circuit)
    save_text(editor, SAME_PORTS)
    gui.reply = QMessageBox.StandardButton.Cancel
    assert not editor.close()
    assert editor.isVisible()


def test_close_with_update(gui, circuit):
    editor = open_editor(gui, circuit)
    save_text(editor, AFTER)
    gui.reply = QMessageBox.StandardButton.Yes
    assert not editor.close()
    assert editor.is_building()
    wait_closed(gui)
    # The port change was asked too, and the editor closed after the update
    assert any("Port 'y' is removed" in question for question in gui.questions)
    assert set(yosys(gui).interface()) == {"a", "b", "z", "q"}
    assert gui.window.verilog_editors.editors() == []


def test_close_with_a_failed_update(gui, circuit):
    editor = open_editor(gui, circuit)
    save_text(editor, "module m(input a; endmodule\n")
    gui.reply = QMessageBox.StandardButton.Yes
    editor.close()
    for _ in range(1500):
        if not editor.is_building():
            break
        spin(20)
    spin()
    # It stays open with the error, and closing asks again
    assert editor.isVisible()
    assert editor.build_panel.step_status()[-1] == ("✗", "List modules")
    assert editor.code.marks()
    gui.reply = QMessageBox.StandardButton.No
    assert editor.close()
    assert len(gui.questions) == 2


def test_close_with_the_port_change_cancelled(gui, circuit):
    editor = open_editor(gui, circuit)
    save_text(editor, AFTER)
    gui.reply = QMessageBox.StandardButton.Yes
    gui.answer = QMessageBox.StandardButton.Cancel
    editor.close()
    for _ in range(1500):
        if not editor.is_building():
            break
        spin(20)
    spin()
    assert editor.isVisible()
    assert set(yosys(gui).interface()) == {"a", "b", "y", "q"}


def test_no_question_when_updated(gui, circuit):
    editor = open_editor(gui, circuit)
    editor.code.setPlainText(SAME_PORTS)
    assert build(editor)[-1] == ("✓", "Update components")
    assert editor.close()
    assert gui.questions == []


def test_no_question_after_reload(gui, circuit):
    editor = open_editor(gui, circuit)
    save_text(editor, SAME_PORTS)
    reload(gui)
    assert editor.close()
    assert gui.questions == []


def test_no_question_without_components(gui, work_dir):
    path = work_dir / "alone.v"
    path.write_text(BEFORE, encoding="utf-8")
    editor = open_editor(gui, path)
    save_text(editor, SAME_PORTS)
    assert editor.close()
    assert gui.questions == []


def test_no_question_when_digsim_closes(gui, circuit):
    editor = open_editor(gui, circuit)
    save_text(editor, SAME_PORTS)
    gui.model._changed = False
    assert gui.window.close()
    assert gui.questions == []
    assert not editor.isVisible()


# Settings of a Yosys component


def test_settings_in_the_context_menu(gui, circuit):
    component_object = gui.model.objects.components.get_object(yosys(gui))
    menu = ComponentContextMenu(gui.window, gui.model, component_object)
    assert "Settings" in [action.text() for action in menu.actions()]


def test_change_settings(gui, circuit):
    component_object = gui.model.objects.components.get_object(yosys(gui))
    gui.model.objects.components.update_settings(
        component_object, {"functional": True, "signals": True}
    )
    spin()
    assert gui.errors == []
    assert yosys(gui).functional
    assert connections(gui) == ["PushButton.O>m.a", "StaticValue.O>m.b", "m.y>Led.I"]
    # Undo gives the gates back, redo the functional blocks
    gui.model.objects.undo()
    spin()
    assert not yosys(gui).functional
    gui.model.objects.redo()
    spin()
    assert yosys(gui).functional
    # The editor synthesizes into functional blocks now
    editor = open_editor(gui, circuit)
    editor.code.setPlainText(SAME_PORTS)
    assert ("✓", "Synthesize into functional blocks") in build(editor)


def test_settings_error(gui, circuit):
    component_object = gui.model.objects.components.get_object(yosys(gui))
    undo_steps = len(gui.model.objects._undo_stack)
    # The ports of the file changed since it was loaded
    circuit.write_text(AFTER, encoding="utf-8")
    gui.model.objects.components.update_settings(
        component_object, {"functional": True, "signals": False}
    )
    spin()
    (error,) = gui.errors
    assert "reload the component first" in error
    assert not yosys(gui).functional
    assert len(gui.model.objects._undo_stack) == undo_steps
    assert connections(gui) == ["PushButton.O>m.a", "StaticValue.O>m.b", "m.y>Led.I"]


def test_open_netlist_asks_no_synthesis(gui, work_dir, monkeypatch):
    verilog = work_dir / "m.v"
    verilog.write_text(BEFORE, encoding="utf-8")
    import json

    netlist = work_dir / "m.json"
    netlist.write_text(json.dumps(YosysComponent.synthesize_file(verilog)), encoding="utf-8")
    add_yosys_from_dialog(gui, monkeypatch, "open", netlist)
    assert len(gui.asked) == 1 and "internal signals" in gui.asked[0]
    # A Verilog file has both
    add_yosys_from_dialog(gui, monkeypatch, "open", verilog)
    assert len(gui.asked) == 2 and "functional blocks" in gui.asked[0]
    # Settings of the netlist component: only the signals
    component = next(
        component
        for component in gui.model.objects.circuit.get_toplevel_components()
        if isinstance(component, YosysComponent) and component.source_file == str(netlist)
    )
    assert set(component.get_reconfigurable_parameters()) == {"signals"}


def test_dialogs_have_only_a_close_button(gui):
    from digsim.app.gui._warning_dialog import WarningDialog
    from digsim.app.settings import ComponentSettingsDialog
    from digsim.app.settings._component_settings import OpenOrNewDialog
    from digsim.app.settings._gui_settings import GuiSettingsDialog
    from digsim.app.settings._shortcut_dialog import ShortcutDialog

    parameters = {"signals": YosysComponent.get_parameters()["signals"]}
    dialogs = [
        WarningDialog(gui.window, "Warning", "text"),
        OpenOrNewDialog(gui.window),
        ComponentSettingsDialog(gui.window, gui.model, "m", parameters),
        GuiSettingsDialog(gui.window, gui.model),
        ShortcutDialog(gui.window, gui.model),
    ]
    for dialog in dialogs:
        flags = dialog.windowFlags()
        assert not flags & Qt.WindowType.WindowMaximizeButtonHint, dialog
        assert not flags & Qt.WindowType.WindowMinimizeButtonHint, dialog
        assert flags & Qt.WindowType.WindowCloseButtonHint, dialog
    # The dialogs with only choices and settings can't be resized
    for dialog in dialogs[1:2] + dialogs[3:]:
        dialog.show()
        spin()
        assert dialog.minimumSize() == dialog.maximumSize(), dialog
        dialog.close()


def test_file_that_cant_be_read_opens_no_editor(gui, work_dir):
    """A file that is not UTF-8: an error, no editor, and the file is not emptied"""
    path = work_dir / "latin1.v"
    content = b"module m(input a, output y); // \xa9 2026\n    assign y = a;\nendmodule\n"
    path.write_bytes(content)
    gui.model.sig_edit_verilog.emit(str(path))
    spin()
    assert gui.window.verilog_editors.editors() == []
    (error,) = gui.errors
    assert "Could not read" in error
    # An editor that couldn't read its file doesn't save over it
    editor = VerilogEditor(gui.model, path)
    assert not editor.loaded
    assert not editor.save()
    assert path.read_bytes() == content
    editor.deleteLater()


# A change of ports builds the whole circuit again: the other Yosys components from the
# netlists they have, not from their files


def add_second_yosys(gui: Gui, work_dir: Path, text: str = BEFORE):
    """Another Yosys component, from b.v, with a wire to a LED"""
    path = work_dir / "b.v"
    path.write_text(text.replace("module m(", "module b("), encoding="utf-8")
    other = gui.add("YosysComponent", 300, 400, path=str(path))
    led = gui.add("Led", 600, 400)
    # Into the scene as the GUI adds a component (synchronizing again would delete the
    # component objects of the scene)
    from digsim.app.gui._circuit_area import CircuitArea

    scene = gui.window.findChild(CircuitArea).scene()
    for component in (other, led):
        scene.add_scene_component(gui.model.objects.components.get_object(component))
    gui.model.objects.wires.connect_ports(other.y, led.I)
    spin()
    return path


def names(gui: Gui) -> set[str]:
    return {component.name() for component in gui.model.objects.circuit.get_toplevel_components()}


def b_keeps_its_netlist(gui: Gui) -> None:
    """b is built again as it was, with its wire, and the circuit has all components"""
    b = yosys_component(gui, "b")
    assert set(b.interface()) == {"a", "b", "y", "q"}
    assert any(connection.startswith("b.y>") for connection in connections(gui))
    assert gui.warnings == []


def test_port_change_with_a_broken_other_component(gui, circuit, work_dir):
    """Another Yosys component whose file has an error now: it keeps its netlist"""
    other = add_second_yosys(gui, work_dir)
    other.write_text("module b(input a; endmodule\n", encoding="utf-8")
    before = names(gui)
    editor = open_editor(gui, circuit)
    editor.code.setPlainText(AFTER)
    assert build(editor)[-1] == ("✓", "Update components")
    assert names(gui) == before
    assert set(yosys_component(gui, "m").interface()) == {"a", "b", "z", "q"}
    b_keeps_its_netlist(gui)


def test_port_change_with_changed_ports_of_another_component(gui, circuit, work_dir):
    """The ports of b changed in its file: b keeps the ports it has until it is reloaded"""
    other = add_second_yosys(gui, work_dir)
    other.write_text(AFTER.replace("module m(", "module b("), encoding="utf-8")
    editor = open_editor(gui, circuit)
    editor.code.setPlainText(AFTER)
    assert build(editor)[-1] == ("✓", "Update components")
    b_keeps_its_netlist(gui)


def test_port_change_with_a_good_other_component(gui, circuit, work_dir):
    add_second_yosys(gui, work_dir)
    editor = open_editor(gui, circuit)
    editor.code.setPlainText(AFTER)
    assert build(editor)[-1] == ("✓", "Update components")
    b_keeps_its_netlist(gui)


def test_port_change_reloaded_with_a_broken_other_component(gui, circuit, work_dir):
    other = add_second_yosys(gui, work_dir)
    other.write_text("module b(input a; endmodule\n", encoding="utf-8")
    circuit.write_text(AFTER, encoding="utf-8")
    reload_component(gui, "m")
    assert set(yosys_component(gui, "m").interface()) == {"a", "b", "z", "q"}
    b_keeps_its_netlist(gui)


def test_rebuild_keeps_undo_when_a_component_is_lost(gui, circuit, work_dir, monkeypatch):
    """The safety net: a component lost in the rebuild keeps the undo steps"""
    other = add_second_yosys(gui, work_dir)
    other.write_text("module b(input a; endmodule\n", encoding="utf-8")
    # b is not given its netlist: it is built from its file, which has an error
    monkeypatch.setattr(YosysComponent, "given_netlists", lambda netlists: nullcontext())
    editor = open_editor(gui, circuit)
    editor.code.setPlainText(AFTER)
    build(editor)
    assert any("Not built again: b" in warning for warning in gui.warnings)
    assert gui.model.objects.can_undo()


def test_port_changes_worked_out_once(gui, circuit, monkeypatch):
    import digsim.app.model._model_components as model_components

    calls = []
    interface_changes = model_components.interface_changes

    def counting(*args):
        calls.append(args)
        return interface_changes(*args)

    monkeypatch.setattr(model_components, "interface_changes", counting)
    editor = open_editor(gui, circuit)
    editor.code.setPlainText(AFTER)
    assert build(editor)[-1] == ("✓", "Update components")
    # One component: once
    assert len(calls) == 1


def test_reload_picks_up_an_include_file(gui, work_dir):
    """Reload runs Yosys again: the netlist of the file depends on the files it includes"""
    defs = work_dir / "defs.vh"
    defs.write_text("`define VALUE 1'b1\n", encoding="utf-8")
    path = work_dir / "inc.v"
    path.write_text(
        '`include "defs.vh"\nmodule inc(input a, output y);\n    assign y = `VALUE;\nendmodule\n',
        encoding="utf-8",
    )
    component = gui.add("YosysComponent", 0, 0, path=str(path))
    gui.model.objects.circuit.run(ms=1)
    assert component.y.value == 1
    defs.write_text("`define VALUE 1'b0\n", encoding="utf-8")
    reload_component(gui, "inc")
    gui.model.objects.circuit.run(ms=1)
    assert component.y.value == 0


def test_no_editing_while_synthesizing(gui, circuit):
    """The file is not changed while Yosys reads it"""
    editor = open_editor(gui, circuit)
    editor.code.setPlainText(SAME_PORTS)
    editor.menu_actions["synthesize"].trigger()
    assert editor.is_building()
    assert editor.code.isReadOnly()
    for name in ("save", "revert", "format", "synthesize", "parameters"):
        assert not editor.menu_actions[name].isEnabled(), name
    for _ in range(1500):
        if not editor.is_building():
            break
        spin(20)
    spin()
    assert not editor.code.isReadOnly()
    for name in ("save", "revert", "format", "synthesize", "parameters"):
        assert editor.menu_actions[name].isEnabled(), name
    assert not editor.needs_update()


def test_unexpected_error_in_synthesis(gui, circuit, monkeypatch):
    """An error that the build steps don't expect ends the build too"""
    import digsim.app.editor._build_panel as build_panel

    def broken(*_):
        raise RuntimeError("the WebAssembly Yosys trapped")

    monkeypatch.setattr(build_panel, "run_synthesis", broken)
    editor = open_editor(gui, circuit)
    steps = build(editor)
    assert steps[-1] == ("✗", "Synthesis")
    assert not editor.is_building()
    assert editor.menu_actions["synthesize"].isEnabled()
    item = editor.build_panel.messages.topLevelItem(0)
    assert "the WebAssembly Yosys trapped" in item.text(2)


# The parameters dialog of the editor

PARAMETERS = """
module m #(parameter WIDTH = 4, parameter INVERT = 0) (
   input a, input [WIDTH-1:0] b, output y, output [WIDTH-1:0] q
);
   assign y = INVERT ? ~a : a;
   assign q = b;
endmodule
"""


@pytest.fixture(name="parameters_circuit")
def fixture_parameters_circuit(gui, circuit):
    """The circuit, with a module with parameters (the same ports with their defaults)"""
    circuit.write_text(PARAMETERS, encoding="utf-8")
    reload(gui)
    assert gui.questions == []
    return circuit


def set_parameters(
    gui: Gui, monkeypatch, editor: VerilogEditor, values: dict[tuple[str, str], str]
) -> list:
    """
    Open the parameters dialog, type values (by (parameter, component)), click
    Synthesize, and wait for the build. Returns the dialogs.
    """
    from PySide6.QtWidgets import QDialog

    from digsim.app.editor._parameters_dialog import ParametersDialog

    dialogs = []

    def exec_(dialog: ParametersDialog) -> int:
        dialogs.append(dialog)
        table = dialog.table
        columns = [table.horizontalHeaderItem(c).text() for c in range(table.columnCount())]
        rows = [table.item(r, 0).text() for r in range(table.rowCount())]
        for (parameter, component), text in values.items():
            table.item(rows.index(parameter), columns.index(component)).setText(text)
        dialog.accept()
        return dialog.result()

    monkeypatch.setattr(ParametersDialog, "exec", exec_)
    editor.menu_actions["parameters"].trigger()
    for _ in range(1500):
        if not editor.is_building():
            break
        spin(20)
    spin()
    assert dialogs and dialogs[-1].result() == QDialog.DialogCode.Accepted
    return dialogs


def test_parameters_with_the_same_ports(gui, parameters_circuit, monkeypatch):
    editor = open_editor(gui, parameters_circuit)
    undo_steps = len(gui.model.objects._undo_stack)
    (dialog,) = set_parameters(gui, monkeypatch, editor, {("INVERT", "m"): "1"})
    table = dialog.table
    assert [table.item(row, 1).text() for row in range(2)] == ["4", "0"]
    assert editor.build_panel.step_status()[-1] == ("✓", "Update components")
    assert gui.questions == [] and gui.errors == [] and gui.warnings == []
    assert yosys(gui).parameters == {"INVERT": 1}
    assert connections(gui) == ["PushButton.O>m.a", "StaticValue.O>m.b", "m.y>Led.I"]
    assert len(gui.model.objects._undo_stack) == undo_steps + 1
    # The dialog shows the values a component has
    (dialog,) = set_parameters(gui, monkeypatch, editor, {})
    assert dialog.table.item(1, 2).text() == "1"
    gui.model.objects.undo()
    spin()
    assert yosys(gui).parameters == {"INVERT": 1}
    gui.model.objects.undo()
    spin()
    assert yosys(gui).parameters == {}


def test_parameters_with_changed_ports(gui, parameters_circuit, monkeypatch):
    editor = open_editor(gui, parameters_circuit)
    set_parameters(gui, monkeypatch, editor, {("WIDTH", "m"): "8"})
    (question,) = gui.questions
    assert "Port 'b' has 8 bits instead of 4" in question
    component = yosys(gui)
    assert component.interface()["b"] == ("input", 8)
    assert component.settings_to_dict()["parameters"] == "WIDTH=8"
    assert connections(gui) == ["PushButton.O>m.a", "m.y>Led.I"]
    # All defaults again
    set_parameters(gui, monkeypatch, editor, {("WIDTH", "m"): ""})
    assert yosys(gui).parameters == {}
    assert yosys(gui).interface()["b"] == ("input", 4)


def test_parameters_cancelled_with_the_ports(gui, parameters_circuit, monkeypatch):
    editor = open_editor(gui, parameters_circuit)
    gui.answer = QMessageBox.StandardButton.Cancel
    set_parameters(gui, monkeypatch, editor, {("WIDTH", "m"): "8"})
    assert yosys(gui).parameters == {}
    # The values were for that synthesis only
    gui.answer = QMessageBox.StandardButton.Ok
    build(editor)
    assert yosys(gui).parameters == {}


def test_parameters_of_two_components(gui, parameters_circuit, monkeypatch):
    gui.add("YosysComponent", 300, 300, path=str(parameters_circuit))
    editor = open_editor(gui, parameters_circuit)
    set_parameters(gui, monkeypatch, editor, {("INVERT", "m_1"): "1"})
    assert yosys_component(gui, "m").parameters == {}
    assert yosys_component(gui, "m_1").parameters == {"INVERT": 1}
    steps = [name for _, name in editor.build_panel.step_status()]
    assert "Synthesize into gates (INVERT=1)" in steps and "Synthesize into gates" in steps


def test_parameter_that_is_not_a_number():
    from digsim.app.editor._parameters_dialog import ParametersDialog

    QApplication.instance() or QApplication([])
    dialog = ParametersDialog(None, "m", {"WIDTH": 4, "INVERT": 0}, {"m": {}, "m_1": {}})
    dialog.table.item(1, 3).setText("yes")
    dialog.accept()
    assert dialog.result() != 1
    assert dialog.error.text() == "m_1: INVERT is not an integer: 'yes'"
    assert dialog.table.item(1, 3).background().color().red() == 255
    dialog.table.item(1, 3).setText("0x1")
    assert dialog.values() == {"m": "", "m_1": "INVERT=1"}
    dialog.clear()
    assert dialog.values() == {"m": "", "m_1": ""}


def test_module_without_parameters(gui, circuit, monkeypatch):
    messages = []
    monkeypatch.setattr(
        QMessageBox, "information", lambda _parent, _title, text, *_: messages.append(text)
    )
    editor = open_editor(gui, circuit)
    editor.menu_actions["parameters"].trigger()
    assert messages == ["The module m has no parameters."]
    assert not editor.is_building()
