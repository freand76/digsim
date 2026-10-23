# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""The main window and widgets of the digsim gui application"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent, QKeyEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from digsim.app.editor import VerilogEditors

from ._circuit_area import CircuitArea
from ._component_selection import ComponentSelection
from ._top_bar import TopBar
from ._utils import are_you_sure_destroy_circuit
from ._warning_dialog import WarningDialog


if TYPE_CHECKING:
    from digsim.app.model import AppModel


class CircuitEditor(QWidget):
    """
    The circuit editor, the component selection widget and the circuit area widget.
    """

    def __init__(self, app_model: AppModel, parent: QWidget) -> None:
        super().__init__(parent)
        self._app_model = app_model
        self._app_model.sig_control_notify.connect(self._control_notify)

        layout = QHBoxLayout(self)
        self.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)
        # A small gap between the component selection and the circuit area
        layout.setSpacing(4)

        self._selection_area = QScrollArea(self)
        self._selection_area.setFixedWidth(106)
        self._selection_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self._selection_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._circuit_area = CircuitArea(app_model, self)
        selection_panel = ComponentSelection(self._circuit_area, self)

        self._selection_area.setWidget(selection_panel)

        layout.addWidget(self._selection_area)
        layout.addWidget(self._circuit_area, 1)
        self._circuit_area.setFocus()

    def _control_notify(self) -> None:
        self._selection_area.setEnabled(not self._app_model.is_running)

    @property
    def circuit_area(self) -> CircuitArea:
        """Get the circuit area"""
        return self._circuit_area


class CentralWidget(QWidget):
    """
    The central widget with the top widget and circuit editor widget.
    """

    def __init__(self, app_model: AppModel, parent: QWidget) -> None:
        super().__init__(parent)
        self._app_model = app_model

        layout = QVBoxLayout(self)
        self.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        circuit_editor = CircuitEditor(app_model, self)
        top_bar = TopBar(app_model, circuit_editor, self)
        layout.addWidget(top_bar)
        layout.setStretchFactor(top_bar, 0)

        layout.addWidget(circuit_editor)
        layout.setStretchFactor(circuit_editor, 1)


class MainWindow(QMainWindow):
    """
    The main window for the application.
    """

    def __init__(self, app_model: AppModel, package_version: str) -> None:
        super().__init__()

        self._app_model = app_model
        self.resize(1280, 720)
        central_widget = CentralWidget(app_model, self)
        self.setWindowTitle(f"DigSim - Interactive Digital Logic Simulator [v{package_version}]")
        self.setCentralWidget(central_widget)
        self.setAcceptDrops(True)  # Needed to avoid "No drag target set."
        self._app_model.sig_error.connect(self.error_dialog)
        self._app_model.sig_warning_log.connect(self.warning_log_dialog)
        self.verilog_editors = VerilogEditors(app_model, self)
        self._app_model.sig_edit_verilog.connect(self.verilog_editors.open)
        self._app_model.sig_yosys_updated.connect(self.verilog_editors.components_updated)

        QShortcut(QKeySequence("Ctrl+Z"), self, self._app_model.objects.undo)
        QShortcut(QKeySequence("Ctrl+Y"), self, self._app_model.objects.redo)
        QShortcut(QKeySequence("Ctrl++"), self, self._app_model.zoom_in)
        QShortcut(QKeySequence("Ctrl+-"), self, self._app_model.zoom_out)
        QShortcut(QKeySequence("Del"), self, self._app_model.objects.delete_selected)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """QT event callback function"""
        super().keyPressEvent(event)
        if event.isAutoRepeat():
            event.accept()
            return

        if event.key() == Qt.Key.Key_Space:
            if self._app_model.is_running:
                self._app_model.model_stop()
            else:
                self._app_model.model_start()
            event.accept()
            return

        if self._app_model.is_running:
            self._app_model.shortcuts.press(event.key())
            event.accept()
            return

        if event.key() == Qt.Key.Key_Escape:
            self._app_model.model_abort_wire()
            event.accept()
        elif event.key() == Qt.Key.Key_Backspace:
            self._app_model.model_remove_wire_corner()
            event.accept()

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        """QT event callback function"""
        super().keyReleaseEvent(event)
        if event.isAutoRepeat():
            event.accept()
            return
        if self._app_model.is_running:
            self._app_model.shortcuts.release(event.key())
            event.accept()

    def error_dialog(self, error_message: str) -> None:
        """Execute Error dialog"""
        QMessageBox.critical(self, "Error!", error_message, QMessageBox.StandardButton.Ok)

    def warning_log_dialog(self, title: str, warning_message: str) -> None:
        """Execute warning log dialog"""
        warning_dialog = WarningDialog(self, title, warning_message)
        warning_dialog.exec()

    def closeEvent(self, event: QCloseEvent) -> None:
        """QT event callback function"""
        if not self.verilog_editors.close_all():
            event.ignore()
            return
        if not self._app_model.is_changed or are_you_sure_destroy_circuit(
            self, "Close Application"
        ):
            # Stops the simulation thread and waits for it
            self._app_model.model_stop()
            super().closeEvent(event)
        else:
            event.ignore()
