# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""The build steps, messages and Yosys log of the Verilog editor, and its synthesis thread"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QColor, QFontDatabase
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QPlainTextEdit,
    QSplitter,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from digsim.app._build_flow import BuildResult, BuildStep, run_synthesis
from digsim.synth import YosysMessage


_SYMBOLS = {"running": "…", "ok": "✓", "warning": "⚠", "error": "✗", "skipped": "–"}
_COLORS = {"ok": "#3a9d5d", "warning": "#d89b28", "error": "#e05252"}


class SynthesisWorker(QThread):
    """Runs the synthesis steps (run_synthesis) in a thread of its own"""

    sig_step = Signal(object)
    sig_done = Signal(object)

    def __init__(self, path: Path, variants: set[bool]) -> None:
        super().__init__()
        self._path = path
        self._variants = variants

    def run(self) -> None:
        """Qt: the thread, it always says when it is done"""
        try:
            result = run_synthesis(self._path, self._variants, self.sig_step.emit)
        except Exception as exc:  # noqa: BLE001
            # Not an error of the Verilog, like the WebAssembly Yosys failing: the editor
            # must not wait for a result for ever
            message = f"Unexpected error: {exc!r}"
            self.sig_step.emit(BuildStep("Synthesis", "error", message))
            result = BuildResult(messages=[YosysMessage("error", message)])
        self.sig_done.emit(result)


class BuildPanel(QWidget):
    """The steps of the last build, and its messages and Yosys log"""

    # A message was double-clicked: the line (from 1) to go to
    sig_go_to_line = Signal(int)

    def __init__(self, path: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._path = path
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        splitter = QSplitter(self)
        layout.addWidget(splitter)
        self.steps = QTreeWidget(self)
        self.steps.setHeaderLabels(["", "Step", "Time", "Result"])
        self.steps.setRootIsDecorated(False)
        splitter.addWidget(self.steps)
        self.tabs = QTabWidget(self)
        splitter.addWidget(self.tabs)
        self.messages = QTreeWidget(self)
        self.messages.setHeaderLabels(["", "Line", "Message"])
        self.messages.setRootIsDecorated(False)
        self.messages.itemActivated.connect(self._message_activated)
        self.tabs.addTab(self.messages, "Messages")
        log_widget = QWidget(self)
        log_layout = QVBoxLayout(log_widget)
        log_layout.setContentsMargins(0, 0, 0, 0)
        self.log_filter = QLineEdit(log_widget)
        self.log_filter.setPlaceholderText("Show the lines with...")
        self.log_filter.textChanged.connect(self._show_log)
        self.log = QPlainTextEdit(log_widget)
        self.log.setReadOnly(True)
        self.log.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.log.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        log_layout.addWidget(self.log_filter)
        log_layout.addWidget(self.log)
        self.tabs.addTab(log_widget, "Yosys log")
        splitter.setSizes([300, 600])
        self._log_lines: list[str] = []

    def clear(self) -> None:
        """Start a new build"""
        self.steps.clear()
        self.messages.clear()
        self._log_lines = []
        self._show_log()
        self.tabs.setTabText(0, "Messages")

    def add_step(self, step: BuildStep) -> None:
        """Add a step, or update the last one when it is the same step"""
        count = self.steps.topLevelItemCount()
        item = self.steps.topLevelItem(count - 1) if count else None
        if item is None or item.text(1) != step.name or item.text(0) != _SYMBOLS["running"]:
            item = QTreeWidgetItem(self.steps)
        item.setText(0, _SYMBOLS[step.status])
        item.setText(1, step.name)
        item.setText(2, f"{step.seconds:.2f} s" if step.seconds is not None else "")
        item.setText(3, step.detail)
        item.setToolTip(3, step.detail)
        color = _COLORS.get(step.status)
        if color is not None:
            item.setForeground(0, QColor(color))
        for column in range(3):
            self.steps.resizeColumnToContents(column)

    def step_status(self) -> list[tuple[str, str]]:
        """The steps as (status symbol, name)"""
        items = [self.steps.topLevelItem(n) for n in range(self.steps.topLevelItemCount())]
        return [(item.text(0), item.text(1)) for item in items if item is not None]

    def is_this_file(self, message: YosysMessage) -> bool:
        """True if the message is about the file of the editor"""
        if message.file is None:
            return False
        try:
            return Path(message.file).resolve() == self._path
        except OSError:
            return False

    def show_result(self, result: BuildResult) -> None:
        """Show the messages and the log of a build"""
        self._log_lines = list(result.log)
        self._show_log()
        self.messages.clear()
        for message in result.messages:
            line = message.line if self.is_this_file(message) else None
            item = QTreeWidgetItem(self.messages)
            item.setText(0, _SYMBOLS[message.kind])
            item.setForeground(0, QColor(_COLORS[message.kind]))
            item.setText(1, str(line) if line is not None else "")
            item.setText(2, message.text)
            item.setToolTip(2, message.text)
        for column in range(2):
            self.messages.resizeColumnToContents(column)
        count = len(result.messages)
        self.tabs.setTabText(0, f"Messages ({count})" if count else "Messages")
        self.tabs.setCurrentIndex(0 if count or not result.log else 1)

    def _show_log(self) -> None:
        text = self.log_filter.text().lower()
        lines = [line for line in self._log_lines if text in line.lower()]
        self.log.setPlainText("\n".join(lines))

    def _message_activated(self, item: QTreeWidgetItem) -> None:
        if item.text(1):
            self.sig_go_to_line.emit(int(item.text(1)))
