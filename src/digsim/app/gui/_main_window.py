# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

"""The main window and widgets of the digsim gui application"""

# pylint: disable=too-few-public-methods

from PySide6.QtCore import Qt
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
from ._utils import are_you_sure_messagebox


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

        circuit_area = CircuitArea(app_model, self)
        selection_panel = ComponentSelection(app_model, circuit_area, self)

        self._selection_area.setWidget(selection_panel)

        self.layout().addWidget(self._selection_area)
        self.layout().setStretchFactor(self._selection_area, 0)

        self.layout().addWidget(circuit_area)
        self.layout().setStretchFactor(circuit_area, 1)

    def _control_notify(self, started):
        self._selection_area.setEnabled(not started)


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

        top_bar = TopBar(app_model, self)
        self.layout().addWidget(top_bar)
        self.layout().setStretchFactor(top_bar, 0)

        working_area = CircuitEditor(app_model, self)
        self.layout().addWidget(working_area)
        self.layout().setStretchFactor(working_area, 1)


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

    def error_dialog(self, error_message):
        """Error dialog for circuit area"""
        QMessageBox.critical(self.parent(), "Error!", error_message, QMessageBox.Ok)

    def closeEvent(self, event):
        """QT event callback function"""
        if not self._app_model.has_changes() or are_you_sure_messagebox(
            self.parent(), "Close Application"
        ):
            self._app_model.model_stop()
            self._app_model.wait()
            super().closeEvent(event)
        else:
            event.ignore()
