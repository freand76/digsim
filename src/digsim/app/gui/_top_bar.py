# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""The top bar of the main window/gui application"""

from pathlib import Path

import qtawesome as qta

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStyle,
)

from digsim.app.settings import GuiSettingsDialog

from ._utils import are_you_sure_destroy_circuit


class SimControlWidget(QFrame):
    """
    The widget for controlling the simulation in the top bar
    """

    CONTROL_WIDGET_WIDTH = 120

    def __init__(self, app_model, parent):
        super().__init__(parent)
        self._time_s = 0
        self._app_model = app_model
        self.setLayout(QHBoxLayout(self))
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(5)
        self._start_button = QPushButton("Start Simulation", self)
        self._start_button.clicked.connect(self._start_stop)
        self._start_button.setMinimumWidth(self.CONTROL_WIDGET_WIDTH)
        self.layout().addWidget(self._start_button)
        self._single_step_button = QPushButton("Single Step", self)
        self._single_step_button.clicked.connect(self._single_step)
        self._single_step_button.setMinimumWidth(self.CONTROL_WIDGET_WIDTH)
        self.layout().addWidget(self._single_step_button)
        self._reset_button = QPushButton("Reset Simulation", self)
        self._reset_button.clicked.connect(self._reset)
        self._reset_button.setEnabled(False)
        self._reset_button.setMinimumWidth(self.CONTROL_WIDGET_WIDTH)
        self.layout().addWidget(self._reset_button)
        self._app_model.sig_control_notify.connect(self._control_notify)
        self._app_model.sig_sim_time_notify.connect(self._sim_time_notify)

    def _start_stop(self):
        """Button action: Start/Stop"""
        if not self._app_model.is_running:
            self._start_button.setEnabled(False)
            self._app_model.model_start()
        else:
            self._start_button.setEnabled(False)
            self._app_model.model_stop()

    def _single_step(self):
        """Button action: Reset"""
        self._start_button.setEnabled(False)
        self._single_step_button.setEnabled(False)
        self._app_model.model_single_step()

    def _reset(self):
        """Button action: Reset"""
        self._app_model.model_reset()

    def _control_notify(self):
        if self._app_model.is_running:
            self._start_button.setText("Stop Similation")
            self._start_button.setEnabled(True)
            self._single_step_button.setEnabled(False)
        else:
            self._start_button.setText("Start Similation")
            self._start_button.setEnabled(True)
            self._single_step_button.setEnabled(True)
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


class VcdFilenameWidget(QFrame):
    """
    The widget showing the vcd filename
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Sunken)
        self.setLayout(QHBoxLayout(self))
        self.layout().setContentsMargins(5, 1, 5, 1)
        self.layout().setSpacing(5)
        self._vcd_filename = QLabel("<vcd file>")
        self._vcd_filename.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._vcd_filename.setMinimumWidth(200)
        self.layout().addWidget(self._vcd_filename)

    def set_filename(self, filename):
        """Set filename in VcdFilenameWdiget"""
        self._vcd_filename.setText(filename)


class VcdControlWidget(QFrame):
    """
    The widget for controlling the vcd output file
    """

    def __init__(self, app_model, parent):
        super().__init__(parent)
        self._app_model = app_model
        self._vcd_filename = None
        self.setLayout(QHBoxLayout(self))
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(5)
        self._enable_vcd = QCheckBox("VCD output", self)
        self._enable_vcd.stateChanged.connect(self._enable)
        self._vcd_path = QPushButton("", self)
        self._vcd_path.setIcon(self.style().standardIcon(QStyle.SP_FileIcon))
        self._vcd_path.clicked.connect(self._change_vcd_file)
        self._vcd_path.setToolTip("Select VCD output")
        self._filename_widget = VcdFilenameWidget(self)
        self.layout().addWidget(self._enable_vcd)
        self.layout().addWidget(self._vcd_path)
        self.layout().addWidget(self._filename_widget)
        self._enable_buttons(False)
        self._app_model.sig_control_notify.connect(self._control_notify)

    def _enable_buttons(self, enable):
        self._vcd_path.setEnabled(enable)
        self._filename_widget.setEnabled(enable)

    def _control_notify(self):
        self._enable_vcd.setEnabled(not self._app_model.is_running)
        self._enable_buttons(not self._app_model.is_running and self._enable_vcd.isChecked())

    def _disable_vcd_selection(self):
        self._enable_vcd.setChecked(False)
        self._enable_buttons(False)

    def _start_vcd(self, filename):
        self._vcd_filename = filename
        display_filename = Path(self._vcd_filename).name
        self._filename_widget.set_filename(display_filename)
        self._enable_buttons(True)
        # Close old vcd (if any)
        self._app_model.objects.circuit.vcd_close()
        # Enable VCD in the model
        self._app_model.objects.circuit.vcd(self._vcd_filename)

    def _open_filedialog(self):
        default_filename = self._vcd_filename
        if default_filename is None:
            default_filename = "vcd_file.vcd"
        path = QFileDialog.getSaveFileName(
            self, "VCD Output name", default_filename, "VCD Files (*.vcd);;All Files (*.*)"
        )
        if len(path[0]) == 0:
            return None
        return path[0]

    def _change_vcd_file(self):
        filename = self._open_filedialog()
        if filename is not None:
            self._start_vcd(filename)

    def _enable(self, _):
        is_checked = self._enable_vcd.isChecked()
        if is_checked:
            if self._vcd_filename is not None:
                self._enable_buttons(True)
            else:
                filename = self._open_filedialog()

                if filename is not None:
                    self._enable_buttons(True)
                    self._start_vcd(filename)
                else:
                    QTimer.singleShot(0, self._disable_vcd_selection)
        else:
            self._enable_buttons(False)
            # Disable VCD in the model
            self._app_model.objects.circuit.vcd_close()


class LoadSaveWidget(QFrame):
    """
    The widget with load/save buttons in the top bar
    """

    def __init__(self, app_model, circuit_editor, parent):
        super().__init__(parent)
        self._app_model = app_model
        self._circuit_editor = circuit_editor
        self.setLayout(QHBoxLayout(self))
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(5)
        self._zoom_in_button = QPushButton("", self)
        self._zoom_in_button.setIcon(qta.icon("msc.zoom-in"))
        self._zoom_in_button.clicked.connect(self._app_model.zoom_in)
        self._zoom_out_button = QPushButton("", self)
        self._zoom_out_button.setIcon(qta.icon("msc.zoom-out"))
        self._zoom_out_button.clicked.connect(self._app_model.zoom_out)
        self._zoom_out_button.setToolTip("Zoom out")
        self.layout().addWidget(self._zoom_in_button)
        self.layout().addWidget(self._zoom_out_button)
        self._delete_button = QPushButton("", self)
        self._delete_button.setIcon(qta.icon("mdi.delete-forever"))
        self._delete_button.clicked.connect(self._app_model.objects.delete_selected)
        self._delete_button.setToolTip("Delete")
        self.layout().addWidget(self._delete_button)
        self._undo_button = QPushButton("", self)
        self._undo_button.setIcon(qta.icon("mdi.undo"))
        self._undo_button.setToolTip("Undo")
        self._undo_button.clicked.connect(self._app_model.objects.undo)
        self.layout().addWidget(self._undo_button)
        self._redo_button = QPushButton("", self)
        self._redo_button.setIcon(qta.icon("mdi.redo"))
        self._redo_button.clicked.connect(self._app_model.objects.redo)
        self._redo_button.setToolTip("Redo")
        self.layout().addWidget(self._redo_button)
        self._settings_button = QPushButton("", self)
        self._settings_button.setIcon(qta.icon("mdi.cog"))
        self._settings_button.clicked.connect(self._settings_dialog)
        self._settings_button.setToolTip("Settings")
        self.layout().addWidget(self._settings_button)
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

    def _settings_dialog(self):
        settings_dialog = GuiSettingsDialog(self, self._app_model)
        settings_dialog.start()

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
        self._app_model.clear_circuit()

    def _control_notify(self):
        if self._app_model.is_running:
            self._load_button.setEnabled(False)
            self._save_button.setEnabled(False)
            self._clear_button.setEnabled(False)
            self._delete_button.setEnabled(False)
            self._undo_button.setEnabled(False)
            self._redo_button.setEnabled(False)
            self._settings_button.setEnabled(False)
        else:
            self._load_button.setEnabled(True)
            self._save_button.setEnabled(self._app_model.is_changed)
            self._clear_button.setEnabled(not self._app_model.objects.components.is_empty())
            self._delete_button.setEnabled(self._circuit_editor.circuit_area.has_selection())
            self._undo_button.setEnabled(self._app_model.objects.can_undo())
            self._redo_button.setEnabled(self._app_model.objects.can_redo())
            self._settings_button.setEnabled(True)


class TopBar(QFrame):
    """
    The top widget with the control and status widgets
    """

    def __init__(self, app_model, circuit_editor, parent):
        super().__init__(parent)
        self.setLayout(QHBoxLayout(self))
        self.layout().addWidget(SimControlWidget(app_model, self))
        self.layout().addWidget(SimTimeWidget(app_model, self))
        self.layout().addStretch(1)
        self.layout().addWidget(VcdControlWidget(app_model, self))
        self.layout().addWidget(LoadSaveWidget(app_model, circuit_editor, self))
