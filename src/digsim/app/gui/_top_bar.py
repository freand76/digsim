# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""The top bar of the main window/gui application"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStyle,
    QWidget,
)

from digsim.app.gui_objects import _theme as theme


if TYPE_CHECKING:
    from digsim.app.model import AppModel


class SimControlWidget(QFrame):
    """
    The widget for controlling the simulation in the top bar
    """

    CONTROL_WIDGET_WIDTH = 120

    def __init__(self, app_model: AppModel, parent: QWidget) -> None:
        super().__init__(parent)
        self._time_s: float = 0
        self._app_model = app_model
        layout = QHBoxLayout(self)
        self.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        self._start_button = QPushButton("Start Simulation", self)
        self._start_button.clicked.connect(self._start_stop)
        self._start_button.setMinimumWidth(self.CONTROL_WIDGET_WIDTH)
        layout.addWidget(self._start_button)
        self._single_step_button = QPushButton("Single Step", self)
        self._single_step_button.clicked.connect(self._single_step)
        self._single_step_button.setMinimumWidth(self.CONTROL_WIDGET_WIDTH)
        layout.addWidget(self._single_step_button)
        self._reset_button = QPushButton("Reset Simulation", self)
        self._reset_button.clicked.connect(self._reset)
        self._reset_button.setEnabled(False)
        self._reset_button.setMinimumWidth(self.CONTROL_WIDGET_WIDTH)
        layout.addWidget(self._reset_button)
        self._app_model.sig_control_notify.connect(self._control_notify)
        self._app_model.sig_sim_time_notify.connect(self._sim_time_notify)

    def _start_stop(self) -> None:
        """Button action: Start/Stop"""
        if not self._app_model.is_running:
            self._start_button.setEnabled(False)
            self._app_model.model_start()
        else:
            self._start_button.setEnabled(False)
            self._app_model.model_stop()

    def _single_step(self) -> None:
        """Button action: Single step"""
        self._start_button.setEnabled(False)
        self._single_step_button.setEnabled(False)
        self._app_model.model_single_step()

    def _reset(self) -> None:
        """Button action: Reset"""
        self._app_model.model_reset()

    def _control_notify(self) -> None:
        if self._app_model.is_running:
            self._start_button.setText("Stop Simulation")
            self._start_button.setEnabled(True)
            self._single_step_button.setEnabled(False)
        else:
            self._start_button.setText("Start Simulation")
            self._start_button.setEnabled(True)
            self._single_step_button.setEnabled(True)
            if self._time_s > 0:
                self._reset_button.setEnabled(True)

    def _sim_time_notify(self, time_s: float) -> None:
        self._time_s = time_s
        if self._time_s and not self._app_model.is_running:
            self._reset_button.setEnabled(True)
        else:
            self._reset_button.setEnabled(False)


class SimTimeWidget(QFrame):
    """
    The widget showing simulation time in the top bar
    """

    def __init__(self, app_model: AppModel, parent: QWidget) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Sunken)
        layout = QHBoxLayout(self)
        self.setLayout(layout)
        layout.setContentsMargins(5, 1, 5, 1)
        layout.setSpacing(5)
        self._app_model = app_model
        sim_time_desc = QLabel("Simulation time:")
        sim_time_desc.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(sim_time_desc)
        self._sim_time = QLabel("0 s")
        self._sim_time.setMinimumWidth(60)
        self._sim_time.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._sim_time)
        self._app_model.sig_sim_time_notify.connect(self._sim_time_notify)
        self._app_model.sig_sim_slow.connect(self._sim_slow)

    def _sim_time_notify(self, time_s: float) -> None:
        self._sim_time.setText(f"{time_s:.2f} s")

    def _sim_slow(self, slow: bool) -> None:
        """The time in red while the simulation is slower than real time"""
        self._sim_time.setStyleSheet(f"color: {theme.WIRE_X.name()}" if slow else "")
        self._sim_time.setToolTip(
            "Slower than real time: the circuit makes many events, like a circuit that oscillates"
            if slow
            else ""
        )


class VcdFilenameWidget(QFrame):
    """
    The widget showing the vcd filename
    """

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Sunken)
        layout = QHBoxLayout(self)
        self.setLayout(layout)
        layout.setContentsMargins(5, 1, 5, 1)
        layout.setSpacing(5)
        self._vcd_filename = QLabel("<vcd file>")
        self._vcd_filename.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self._vcd_filename.setMinimumWidth(200)
        layout.addWidget(self._vcd_filename)

    def set_filename(self, filename: str) -> None:
        """Set the filename shown"""
        self._vcd_filename.setText(filename)


class VcdControlWidget(QFrame):
    """
    The widget for controlling the vcd output file
    """

    def __init__(self, app_model: AppModel, parent: QWidget) -> None:
        super().__init__(parent)
        self._app_model = app_model
        self._vcd_filename: str | None = None
        layout = QHBoxLayout(self)
        self.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        self._enable_vcd = QCheckBox("VCD output", self)
        self._enable_vcd.stateChanged.connect(self._enable)
        self._vcd_path = QPushButton("", self)
        self._vcd_path.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon))
        self._vcd_path.clicked.connect(self._change_vcd_file)
        self._vcd_path.setToolTip("Select VCD output")
        self._filename_widget = VcdFilenameWidget(self)
        layout.addWidget(self._enable_vcd)
        layout.addWidget(self._vcd_path)
        layout.addWidget(self._filename_widget)
        self._enable_buttons(False)
        self._app_model.sig_control_notify.connect(self._control_notify)

    def _enable_buttons(self, enable: bool) -> None:
        self._vcd_path.setEnabled(enable)
        self._filename_widget.setEnabled(enable)

    def _control_notify(self) -> None:
        self._enable_vcd.setEnabled(not self._app_model.is_running)
        self._enable_buttons(not self._app_model.is_running and self._enable_vcd.isChecked())

    def _disable_vcd_selection(self) -> None:
        self._enable_vcd.setChecked(False)
        self._enable_buttons(False)

    def _start_vcd(self, filename: str) -> None:
        # Close old vcd (if any)
        self._app_model.objects.circuit.vcd_close()
        # Enable VCD in the model
        try:
            self._app_model.objects.circuit.vcd(filename)
        except OSError as exc:
            self._app_model.sig_error.emit(f"Could not open VCD file: {exc!s}")
            QTimer.singleShot(0, self._disable_vcd_selection)
            return
        self._vcd_filename = filename
        display_filename = Path(filename).name
        self._filename_widget.set_filename(display_filename)
        self._enable_buttons(True)

    def _open_filedialog(self) -> str | None:
        default_filename = self._vcd_filename
        if default_filename is None:
            default_filename = "vcd_file.vcd"
        path = QFileDialog.getSaveFileName(
            self, "VCD Output name", default_filename, "VCD Files (*.vcd);;All Files (*.*)"
        )
        if len(path[0]) == 0:
            return None
        return path[0]

    def _change_vcd_file(self) -> None:
        filename = self._open_filedialog()
        if filename is not None:
            self._start_vcd(filename)

    def _enable(self, _: int) -> None:
        is_checked = self._enable_vcd.isChecked()
        if is_checked:
            if self._vcd_filename is not None:
                # The VCD was closed when the checkbox was unchecked, start it again
                self._start_vcd(self._vcd_filename)
            else:
                filename = self._open_filedialog()

                if filename is not None:
                    self._start_vcd(filename)
                else:
                    QTimer.singleShot(0, self._disable_vcd_selection)
        else:
            self._enable_buttons(False)
            # Disable VCD in the model
            self._app_model.objects.circuit.vcd_close()


class TopBar(QFrame):
    """
    The top widget with the control and status widgets
    """

    def __init__(self, app_model: AppModel, parent: QWidget) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        self.setLayout(layout)
        layout.addWidget(SimControlWidget(app_model, self))
        layout.addWidget(SimTimeWidget(app_model, self))
        layout.addStretch(1)
        layout.addWidget(VcdControlWidget(app_model, self))
