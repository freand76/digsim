# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

"""The top bar of the main window/gui application"""

# pylint: disable=too-few-public-methods

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QStyle

from ._utils import are_you_sure_destroy_circuit, delete_selected_objects


class SimControlWidget(QFrame):
    """
    The widget for controlling the simulation in the top bar
    """

    def __init__(self, app_model, parent):
        super().__init__(parent)
        self._time_s = 0
        self._started = False
        self._app_model = app_model
        self.setLayout(QHBoxLayout(self))
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(5)
        self._start_button = QPushButton("Start Simulation", self)
        self._start_button.clicked.connect(self.start_stop)
        self.layout().addWidget(self._start_button)
        self._reset_button = QPushButton("Reset Simulation", self)
        self._reset_button.clicked.connect(self.reset)
        self._reset_button.setEnabled(False)
        self.layout().addWidget(self._reset_button)
        self._app_model.sig_control_notify.connect(self._control_notify)
        self._app_model.sig_sim_time_notify.connect(self._sim_time_notify)

    def start_stop(self):
        """Button action: Start/Stop"""
        if not self._started:
            self._started = True
            self._start_button.setEnabled(False)
            self._app_model.model_start()
        else:
            self._started = False
            self._start_button.setEnabled(False)
            self._app_model.model_stop()

    def reset(self):
        """Button action: Reset"""
        self._app_model.model_reset()

    def _control_notify(self):
        if self._app_model.is_running:
            self._start_button.setText("Stop Similation")
            self._start_button.setEnabled(True)
        else:
            self._start_button.setText("Start Similation")
            self._start_button.setEnabled(True)
            if self._time_s > 0:
                self._reset_button.setEnabled(True)

    def _sim_time_notify(self, time_s):
        self._time_s = time_s
        if self._time_s and not self._app_model.is_running:
            self._reset_button.setEnabled(True)
        else:
            self._reset_button.setEnabled(False)


class SimTimeWidget(QFrame):
    """
    The widget showing simulation time in the opt bar
    """

    def __init__(self, app_model, parent):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Sunken)
        self.setLayout(QHBoxLayout(self))
        self.layout().setContentsMargins(5, 1, 5, 1)
        self.layout().setSpacing(5)
        self._app_model = app_model
        sim_time_desc = QLabel("Simulation time:")
        sim_time_desc.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.layout().addWidget(sim_time_desc)
        self._sim_time = QLabel("0 s")
        self._sim_time.setMinimumWidth(60)
        self._sim_time.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.layout().addWidget(self._sim_time)
        self._app_model.sig_sim_time_notify.connect(self._sim_time_notify)

    def _sim_time_notify(self, time_s):
        self._sim_time.setText(f"{time_s:.2f} s")


class LoadSaveWidget(QFrame):
    """
    The widget with load/save buttons in the top bar
    """

    def __init__(self, app_model, parent):
        super().__init__(parent)
        self._app_model = app_model
        self.setLayout(QHBoxLayout(self))
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(5)
        self._delete_button = QPushButton("", self)
        self._delete_button.setIcon(self.style().standardIcon(QStyle.SP_TrashIcon))
        self._delete_button.clicked.connect(self._delete)
        self._delete_button.setToolTip("Delete")
        self.layout().addWidget(self._delete_button)
        self._undo_button = QPushButton("", self)
        self._undo_button.setIcon(self.style().standardIcon(QStyle.SP_ArrowBack))
        self._undo_button.setToolTip("Undo")
        self._undo_button.clicked.connect(self._undo)
        self.layout().addWidget(self._undo_button)
        self._redo_button = QPushButton("", self)
        self._redo_button.setIcon(self.style().standardIcon(QStyle.SP_ArrowForward))
        self._redo_button.clicked.connect(self._redo)
        self._redo_button.setToolTip("Redo")
        self.layout().addWidget(self._redo_button)
        self._load_button = QPushButton("Load Circuit", self)
        self._load_button.clicked.connect(self._load)
        self.layout().addWidget(self._load_button)
        self._save_button = QPushButton("Save Circuit", self)
        self._save_button.clicked.connect(self._save)
        self.layout().addWidget(self._save_button)
        self._clear_button = QPushButton("Clear Circuit", self)
        self._clear_button.clicked.connect(self._clear)
        self.layout().addWidget(self._clear_button)
        self._app_model.sig_control_notify.connect(self._control_notify)
        self._control_notify()

    def _load(self):
        """Button action: Load"""
        if self._app_model.is_changed and not are_you_sure_destroy_circuit(
            self.parent(), "Load circuit"
        ):
            return
        path = QFileDialog.getOpenFileName(
            self, "Load Circuit", "", "Circuit Files (*.circuit);;All Files (*.*)"
        )
        if len(path[0]) == 0:
            return
        self._app_model.load_circuit(path[0])

    def _save(self):
        """Button action: Save"""
        path = QFileDialog.getSaveFileName(
            self, "Save Circuit", "", "Circuit Files (*.circuit);;All Files (*.*)"
        )
        if len(path[0]) == 0:
            return
        self._app_model.save_circuit(path[0])

    def _clear(self):
        """Button action: Save"""
        if are_you_sure_destroy_circuit(self.parent(), "Clear circuit"):
            self._app_model.clear_circuit()

    def _delete(self):
        """Button action: Delete"""
        delete_selected_objects(self._app_model, self)

    def _undo(self):
        """Button action: Undo"""
        self._app_model.objects.undo()

    def _redo(self):
        """Button action: Redo"""
        self._app_model.objects.redo()

    def _control_notify(self):
        if self._app_model.is_running:
            self._load_button.setEnabled(False)
            self._save_button.setEnabled(False)
            self._clear_button.setEnabled(False)
            self._delete_button.setEnabled(False)
            self._undo_button.setEnabled(False)
            self._redo_button.setEnabled(False)
        else:
            self._load_button.setEnabled(True)
            self._save_button.setEnabled(self._app_model.is_changed)
            self._clear_button.setEnabled(not self._app_model.objects.components.is_empty())
            self._delete_button.setEnabled(self._app_model.objects.has_selection())
            self._undo_button.setEnabled(self._app_model.objects.can_undo())
            self._redo_button.setEnabled(self._app_model.objects.can_redo())


class TopBar(QFrame):
    """
    The top widget with the control and status widgets
    """

    def __init__(self, app_model, parent):
        super().__init__(parent)
        self.setLayout(QHBoxLayout(self))
        self.layout().addWidget(SimControlWidget(app_model, self))
        self.layout().addWidget(SimTimeWidget(app_model, self))
        self.layout().addStretch(1)
        self.layout().addWidget(LoadSaveWidget(app_model, self))
