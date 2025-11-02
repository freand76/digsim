# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""The main window and widgets of the digsim gui application"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ._circuit_area import CircuitArea
from ._component_selection import ComponentSelection
from ._top_bar import TopBar
from ._utils import are_you_sure_destroy_circuit
from ._warning_dialog import WarningDialog


class CircuitEditor(QSplitter):
    """
    The circuit editor, the component selction widget and the circuit area widget.
    """

    def __init__(self, app_model, parent):
        super().__init__(parent)
        self._app_model = app_model
        self._app_model.sig_control_notify.connect(self._control_notify)

        self.setLayout(QHBoxLayout(self))
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)

        self._selection_area = QScrollArea(self)
        self._selection_area.setFixedWidth(106)
        self._selection_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self._selection_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._circuit_area = CircuitArea(app_model, self)
        selection_panel = ComponentSelection(app_model, self._circuit_area, self)

        self.layout().addWidget(self._circuit_area)
        self._selection_area.setWidget(selection_panel)

        self.layout().addWidget(self._selection_area)
        self.layout().setStretchFactor(self._selection_area, 0)
        self._circuit_area.setFocus()

    def _control_notify(self):
        self._selection_area.setEnabled(not self._app_model.is_running)

    @property
    def circuit_area(self):
        """Get the circuit area"""
        return self._circuit_area


class CentralWidget(QWidget):
    """
    The central widget with the top widget and circuit editor widget.
    """

    def __init__(self, app_model, parent):
        super().__init__(parent)
        self._app_model = app_model

        self.setLayout(QVBoxLayout(self))
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)

        circuit_editor = CircuitEditor(app_model, self)
        top_bar = TopBar(app_model, circuit_editor, self)
        self.layout().addWidget(top_bar)
        self.layout().setStretchFactor(top_bar, 0)

        self.layout().addWidget(circuit_editor)
        self.layout().setStretchFactor(circuit_editor, 1)


class MainWindow(QMainWindow):
    """
    The main window for the applicaton.
    """

    def __init__(self, app_model):
        super().__init__()

        self._app_model = app_model
        self.resize(1280, 720)
        central_widget = CentralWidget(app_model, self)
        self.setWindowTitle("DigSim - Interactive Digital Logic Simulator")
        self.setCentralWidget(central_widget)
        self.setAcceptDrops(True)  # Needed to avoid "No drag target set."
        self._app_model.sig_error.connect(self.error_dialog)
        self._app_model.sig_warning_log.connect(self.warning_log_dialog)

        QShortcut(QKeySequence("Ctrl+Z"), self, self._app_model.objects.undo)
        QShortcut(QKeySequence("Ctrl+Y"), self, self._app_model.objects.redo)
        QShortcut(QKeySequence("Ctrl++"), self, self._app_model.zoom_in)
        QShortcut(QKeySequence("Ctrl+-"), self, self._app_model.zoom_out)
        QShortcut(QKeySequence("Del"), self, self._app_model.objects.delete_selected)

    def keyPressEvent(self, event):
        """QT event callback function"""
        super().keyPressEvent(event)
        if event.isAutoRepeat():
            event.accept()
            return

        if event.key() == Qt.Key_Space:
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

        if event.key() == Qt.Key_Escape:
            self._app_model.model_abort_wire()
            event.accept()

    def keyReleaseEvent(self, event):
        """QT event callback function"""
        super().keyReleaseEvent(event)
        if event.isAutoRepeat():
            event.accept()
            return
        if self._app_model.is_running:
            self._app_model.shortcuts.release(event.key())
            event.accept()

    def _undo_shortcut(self):
        self._app_model.objects.undo()

    def error_dialog(self, error_message):
        """Execute Error dialog"""
        QMessageBox.critical(self.parent(), "Error!", error_message, QMessageBox.Ok)

    def warning_log_dialog(self, title, warning_message):
        """Execute warning log dialog"""
        warning_dialog = WarningDialog(self, title, warning_message)
        warning_dialog.exec_()

    def closeEvent(self, event):
        """QT event callback function"""
        if not self._app_model.is_changed or are_you_sure_destroy_circuit(
            self.parent(), "Close Application"
        ):
            self._app_model.model_stop()
            self._app_model.wait()
            super().closeEvent(event)
        else:
            event.ignore()
