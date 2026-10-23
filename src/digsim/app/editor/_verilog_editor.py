# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""The Verilog editor window"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QFileSystemWatcher, Qt
from PySide6.QtGui import QAction, QCloseEvent, QKeySequence, QTextCursor
from PySide6.QtWidgets import (
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from digsim.app._build_flow import BuildResult, BuildStep
from digsim.circuit.components.atoms import DigsimException
from digsim.verilog import VerilogFormatError, VerilogFormatter

from ._build_panel import BuildPanel, SynthesisWorker
from ._code_edit import CodeEdit
from ._find_bar import FindBar
from ._yosys_update import update_yosys_components


if TYPE_CHECKING:
    from digsim.app.model import AppModel


def _read(path: Path) -> tuple[str, str]:
    """The text of a file with \\n newlines, and the newline the file has"""
    with open(path, encoding="utf-8", newline="") as file:
        text = file.read()
    newline = "\r\n" if "\r\n" in text else "\n"
    return text.replace("\r\n", "\n"), newline


class VerilogEditor(QMainWindow):
    """
    An editor window for a Verilog file. It edits the file, not a component: it stays
    open when the components of the file are deleted.
    """

    def __init__(self, app_model: AppModel, path: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowFlag(Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self._app_model = app_model
        self._path = path
        self._newline = "\n"
        # The text of the file when it was loaded or saved, to tell our own saves from
        # changes by others
        self._disk_text = ""
        # The text the components of the file were built from, as far as the editor knows:
        # the file when the editor opened, and when they were updated since
        self._built_text = ""
        # The text that the running synthesis was saved with
        self._synthesized_text: str | None = None
        # Close when the components are updated (the answer to the close question)
        self._close_after_build = False
        # Closing because DigSim closes: the components go too, don't offer to update them
        self._closing_app = False
        self.code = CodeEdit(self)
        self.find_bar = FindBar(self.code, self)
        self._position = QLabel(self)
        self.statusBar().addPermanentWidget(self._position)

        editor_widget = QWidget(self)
        editor_layout = QVBoxLayout(editor_widget)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.setSpacing(0)
        editor_layout.addWidget(self.code)
        editor_layout.addWidget(self.find_bar)
        self.build_panel = BuildPanel(path, self)
        self.build_panel.sig_go_to_line.connect(self.code.go_to_line)
        self.build_panel.hide()
        self.splitter = QSplitter(Qt.Orientation.Vertical, self)
        self.splitter.addWidget(editor_widget)
        self.splitter.addWidget(self.build_panel)
        self.splitter.setSizes([500, 200])
        self.setCentralWidget(self.splitter)
        self._worker: SynthesisWorker | None = None

        self._add_menus()
        self.code.document().modificationChanged.connect(self.setWindowModified)
        self.code.cursorPositionChanged.connect(self._show_position)
        self._watcher = QFileSystemWatcher(self)
        self._watcher.fileChanged.connect(self._file_changed)
        self.setWindowTitle(f"{path.name}[*] - Verilog Editor")
        self.resize(900, 700)
        # The text is only saved after the file has been read, or it would be emptied
        self.loaded = self.load()
        self._built_text = self._disk_text

    @property
    def path(self) -> Path:
        """The file"""
        return self._path

    def is_modified(self) -> bool:
        """True if the text has changes that are not saved"""
        return self.code.document().isModified()

    def _action(
        self,
        menu_name: str,
        text: str,
        slot: Callable[[], object],
        shortcut: QKeySequence.StandardKey | str | None = None,
    ) -> QAction:
        menu = self._menus[menu_name]
        action = QAction(text, self)
        if shortcut is not None:
            action.setShortcut(shortcut)
        action.triggered.connect(slot)
        menu.addAction(action)
        return action

    def _add_menus(self) -> None:
        menu_bar = self.menuBar()
        self._menus = {name: menu_bar.addMenu(name) for name in ("&File", "&Edit", "&Build")}
        self.menu_actions: dict[str, QAction] = {}
        Key = QKeySequence.StandardKey
        self.menu_actions["save"] = self._action("&File", "&Save", self.save, Key.Save)
        self.menu_actions["revert"] = self._action("&File", "&Revert to saved", self.revert)
        self._menus["&File"].addSeparator()
        self.menu_actions["close"] = self._action("&File", "&Close", self.close, Key.Close)
        code = self.code
        self.menu_actions["undo"] = self._action("&Edit", "&Undo", code.undo, Key.Undo)
        self.menu_actions["redo"] = self._action("&Edit", "&Redo", code.redo, Key.Redo)
        self._menus["&Edit"].addSeparator()
        self.menu_actions["cut"] = self._action("&Edit", "Cu&t", code.cut, Key.Cut)
        self.menu_actions["copy"] = self._action("&Edit", "&Copy", code.copy, Key.Copy)
        self.menu_actions["paste"] = self._action("&Edit", "&Paste", code.paste, Key.Paste)
        self.menu_actions["select_all"] = self._action(
            "&Edit", "Select &all", code.selectAll, Key.SelectAll
        )
        self._menus["&Edit"].addSeparator()
        self.menu_actions["find"] = self._action(
            "&Edit", "&Find...", self.find_bar.open_bar, Key.Find
        )
        self.menu_actions["find_next"] = self._action(
            "&Edit", "Find &next", self.find_bar.find_next, Key.FindNext
        )
        self.menu_actions["find_previous"] = self._action(
            "&Edit", "Find pre&vious", self.find_bar.find_previous, Key.FindPrevious
        )
        self.menu_actions["replace"] = self._action(
            "&Edit", "R&eplace...", lambda: self.find_bar.open_bar(replace=True), "Ctrl+H"
        )
        self.menu_actions["go_to_line"] = self._action(
            "&Edit", "&Go to line...", self._go_to_line, "Ctrl+G"
        )
        self._menus["&Edit"].addSeparator()
        self.menu_actions["comment"] = self._action(
            "&Edit", "Toggle co&mment", code.toggle_comment, "Ctrl+/"
        )
        self.menu_actions["indent"] = self._action(
            "&Edit", "&Indent", code.indent_selection, "Ctrl+]"
        )
        self.menu_actions["format"] = self._action(
            "&Build", "&Format", self.format_code, "Ctrl+Shift+I"
        )
        self.menu_actions["synthesize"] = self._action(
            "&Build", "&Synthesize", self.synthesize, "Ctrl+B"
        )
        self.menu_actions["unindent"] = self._action(
            "&Edit", "U&nindent", code.unindent_selection, "Ctrl+["
        )
        code.undoAvailable.connect(self.menu_actions["undo"].setEnabled)
        code.redoAvailable.connect(self.menu_actions["redo"].setEnabled)
        code.copyAvailable.connect(self.menu_actions["cut"].setEnabled)
        code.copyAvailable.connect(self.menu_actions["copy"].setEnabled)
        for name in ("undo", "redo", "cut", "copy"):
            self.menu_actions[name].setEnabled(False)

    def _show_position(self) -> None:
        cursor = self.code.textCursor()
        self._position.setText(
            f"Line {cursor.blockNumber() + 1}, column {cursor.positionInBlock() + 1}"
        )

    def _go_to_line(self) -> None:
        line, ok = QInputDialog.getInt(
            self,
            "Go to line",
            "Line:",
            self.code.textCursor().blockNumber() + 1,
            1,
            self.code.blockCount(),
        )
        if ok:
            self.code.go_to_line(line)

    def format_code(self) -> bool:
        """
        Format the text (see VerilogFormatter), as one undo step. False with a message if
        the formatter can't.
        """
        text = self.code.toPlainText()
        try:
            formatted = VerilogFormatter(indent=self.code.indent).format(text)
        except VerilogFormatError as exc:
            self.statusBar().showMessage(f"Not formatted: {exc}", 5000)
            return False
        if formatted == text:
            self.statusBar().showMessage("Already formatted", 3000)
            return True
        cursor = self.code.textCursor()
        line = cursor.blockNumber()
        cursor.beginEditBlock()
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.insertText(formatted)
        cursor.endEditBlock()
        # The cursor stays on its line, at the end of the indentation
        block = self.code.document().findBlockByNumber(line)
        if block.isValid():
            cursor.setPosition(block.position() + len(block.text()) - len(block.text().lstrip()))
            self.code.setTextCursor(cursor)
        self.statusBar().showMessage("Formatted", 3000)
        return True

    # The file

    def _watch(self) -> None:
        if self._watcher.files():
            self._watcher.removePaths(self._watcher.files())
        if self._path.exists():
            self._watcher.addPath(str(self._path))

    def load(self) -> bool:
        """Load the file, False with a message if it can't be read"""
        try:
            text, self._newline = _read(self._path)
        except (OSError, UnicodeDecodeError) as exc:
            QMessageBox.critical(self, "Verilog Editor", f"Could not read {self._path}: {exc}")
            return False
        self._disk_text = text
        self.code.setPlainText(text)
        self.code.document().setModified(False)
        self._watch()
        self.loaded = True
        return True

    def save(self) -> bool:
        """Save the file, False with a message if it can't be written"""
        if not self.loaded:
            QMessageBox.critical(
                self, "Verilog Editor", f"{self._path} was not read, it is not saved"
            )
            return False
        text = self.code.toPlainText()
        try:
            with open(self._path, "w", encoding="utf-8", newline="") as file:
                file.write(text.replace("\n", self._newline))
        except OSError as exc:
            QMessageBox.critical(self, "Verilog Editor", f"Could not save {self._path}: {exc}")
            return False
        self._disk_text = text
        self.code.document().setModified(False)
        self.statusBar().showMessage(f"Saved {self._path.name}", 3000)
        self._watch()
        return True

    def revert(self) -> None:
        """Load the file again, without the changes"""
        if self.is_modified():
            answer = QMessageBox.question(
                self,
                "Revert to saved",
                f"Discard the changes to {self._path.name}?",
                QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
            )
            if answer != QMessageBox.StandardButton.Discard:
                return
        self.load()

    def _file_changed(self) -> None:
        """The file was changed by another program: load it, ask if there are changes"""
        self._watch()
        try:
            text, _ = _read(self._path)
        except (OSError, UnicodeDecodeError):
            # Removed, or being written: the next change tells
            return
        if text == self._disk_text:
            return
        if self.is_modified():
            answer = QMessageBox.question(
                self,
                "File changed",
                f"{self._path.name} was changed by another program. Load it, and discard "
                "the changes in the editor?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                # Asked once for this version of the file
                self._disk_text = text
                return
        self.load()

    def maybe_save(self) -> bool:
        """If there are changes, ask to save them. False if cancelled."""
        if not self.is_modified():
            return True
        answer = QMessageBox.question(
            self,
            "Verilog Editor",
            f"Save the changes to {self._path.name}?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
        )
        if answer == QMessageBox.StandardButton.Save:
            return self.save()
        return answer == QMessageBox.StandardButton.Discard

    def components_updated(self) -> None:
        """The components of the file were updated from it (by the editor or by Reload)"""
        # The editor's own synthesis: the text it saved and synthesized
        self._built_text = (
            self._synthesized_text if self._synthesized_text is not None else self._disk_text
        )

    def needs_update(self) -> bool:
        """True if components use the file, and were built from another text than the saved"""
        if self._disk_text == self._built_text:
            return False
        return bool(self._app_model.objects.components.yosys_components(str(self._path)))

    def close_for_app(self) -> bool:
        """Close because DigSim closes: ask to save, not to update the components"""
        self._closing_app = True
        closed = self.close()
        self._closing_app = False
        return closed

    def _ask_update(self) -> QMessageBox.StandardButton:
        return QMessageBox.question(
            self,
            "Verilog Editor",
            f"The components of {self._path.name} are not updated with the saved file. "
            "Synthesize it and update them before closing?",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No
            | QMessageBox.StandardButton.Cancel,
        )

    def closeEvent(self, event: QCloseEvent) -> None:
        """Qt: ask to save the changes, and to update the components with them"""
        if not self.maybe_save():
            event.ignore()
            return
        if not self._closing_app and self._worker is None and self.needs_update():
            answer = self._ask_update()
            if answer == QMessageBox.StandardButton.Yes:
                # Closed by _synthesized() when the components are updated
                event.ignore()
                self._close_after_build = True
                self.synthesize()
                return
            if answer != QMessageBox.StandardButton.No:
                event.ignore()
                return
        if self._worker is not None:
            # Its result is not used
            self._worker.sig_step.disconnect()
            self._worker.sig_done.disconnect()
            self._worker.wait()
            self._worker = None
        event.accept()

    # Synthesis

    def is_building(self) -> bool:
        """True while Yosys synthesizes"""
        return self._worker is not None

    def _set_building(self, building: bool) -> None:
        # The file is not changed while Yosys reads it: the netlist is of the saved text
        for name in ("synthesize", "format", "save", "revert"):
            self.menu_actions[name].setEnabled(not building)
        self.code.setReadOnly(building)
        if building:
            self.statusBar().showMessage("Synthesizing...")
        else:
            self.statusBar().clearMessage()

    def synthesize(self) -> None:
        """
        Save the file and synthesize it in a thread, for the components that use it: into
        gates or functional blocks, as they are. When it is done, the components are
        updated (see _synthesized).
        """
        if self._worker is not None:
            return
        panel = self.build_panel
        panel.clear()
        panel.show()
        panel.add_step(BuildStep("Save", "running"))
        if not self.save():
            panel.add_step(BuildStep("Save", "error", f"Could not save {self._path.name}"))
            self._close_after_build = False
            return
        panel.add_step(BuildStep("Save", "ok", self._path.name))
        self._synthesized_text = self._disk_text
        components = self._app_model.objects.components.yosys_components(str(self._path))
        variants = {component.functional for component in components} or {False}
        self._worker = SynthesisWorker(self._path, variants)
        self._worker.sig_step.connect(panel.add_step)
        self._worker.sig_done.connect(self._synthesized)
        self._set_building(True)
        self._worker.start()

    def _synthesized(self, result: BuildResult) -> None:
        """The thread is done: show the messages, and update the components"""
        if self._worker is not None:
            self._worker.wait()
            self._worker = None
        self._set_building(False)
        close_after_build = self._close_after_build
        self._close_after_build = False
        panel = self.build_panel
        panel.show_result(result)
        marks: dict[int, tuple[str, str]] = {}
        for message in result.messages:
            if message.line is None or not panel.is_this_file(message):
                continue
            # An error before a warning on the same line
            if marks.get(message.line, ("",))[0] != "error":
                marks[message.line] = (message.kind, message.text)
        self.code.set_marks(marks)
        if result.netlists is None:
            self._synthesized_text = None
            self.statusBar().showMessage("Synthesis failed", 5000)
            return
        updated = self._update_components(result.netlists)
        self._synthesized_text = None
        if updated and close_after_build:
            self.close()

    def _update_components(self, netlists: dict[bool, dict[str, Any]]) -> bool:
        """Update the components of the file, True if there were any and they were"""
        panel = self.build_panel
        path = str(self._path)
        components = self._app_model.objects.components
        yosys_components = components.yosys_components(path)
        if not yosys_components:
            panel.add_step(
                BuildStep("Update components", "skipped", "No component uses this file")
            )
            return False
        if any(component.functional not in netlists for component in yosys_components):
            panel.add_step(
                BuildStep(
                    "Update components",
                    "error",
                    "The components changed while synthesizing, synthesize again",
                )
            )
            return False
        try:
            update = components.prepare_yosys_update(path, netlists)
        except DigsimException as exc:
            panel.add_step(BuildStep("Check ports", "error", str(exc)))
            return False
        changes = update.port_changes()
        if changes:
            detail = "; ".join(changes.describe())
            removed = len(update.removed)
            if removed:
                detail += f"; {removed} wire{'s' if removed > 1 else ''} removed"
            panel.add_step(BuildStep("Check ports", "warning", detail))
        else:
            panel.add_step(BuildStep("Check ports", "ok", "The same ports"))
        try:
            updated = update_yosys_components(self, self._app_model, update)
        except DigsimException as exc:
            panel.add_step(BuildStep("Update components", "error", str(exc)))
            return False
        if not updated:
            panel.add_step(BuildStep("Update components", "skipped", "Cancelled"))
            return False
        count = len(yosys_components)
        panel.add_step(
            BuildStep("Update components", "ok", f"{count} component{'s' if count > 1 else ''}")
        )
        self.statusBar().showMessage("Synthesized", 5000)
        return True
