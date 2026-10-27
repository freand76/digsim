# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""The menu bar of the main window"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from PySide6.QtCore import QUrl
from PySide6.QtGui import QAction, QDesktopServices, QKeySequence
from PySide6.QtWidgets import QFileDialog, QMenu, QMenuBar, QMessageBox, QWidget

from digsim.app.settings import GuiSettingsDialog

from ._circuit_area import CircuitArea
from ._utils import are_you_sure_destroy_circuit


if TYPE_CHECKING:
    from digsim.app.model import AppModel

DOCUMENTATION_URL = "https://freand76.github.io/digsim/"
CIRCUIT_FILES = "Circuit Files (*.circuit);;All Files (*.*)"


class MenuBar(QMenuBar):
    """
    The menu bar: File, Edit, View, Simulation and Help. The actions that change the
    circuit are off while the simulation runs.
    """

    def __init__(self, app_model: AppModel, parent: QWidget, package_version: str) -> None:
        super().__init__(parent)
        self._app_model = app_model
        self._window = parent
        self._package_version = package_version
        self._time_s: float = 0
        # The circuit area of the window, see set_circuit_area()
        self._circuit_area: CircuitArea | None = None

        file_menu = self.addMenu("&File")
        self._new_action = self._add(file_menu, "&New", self.new_circuit, "Ctrl+N")
        self._open_action = self._add(file_menu, "&Open...", self.open_circuit, "Ctrl+O")
        self._save_action = self._add(file_menu, "&Save", self.save_circuit, "Ctrl+S")
        self._save_as_action = self._add(
            file_menu, "Save &As...", self.save_circuit_as, "Ctrl+Shift+S"
        )
        file_menu.addSeparator()
        self._add(file_menu, "&Quit", parent.close, "Ctrl+Q")

        edit_menu = self.addMenu("&Edit")
        self._undo_action = self._add(edit_menu, "&Undo", self._app_model.objects.undo, "Ctrl+Z")
        self._redo_action = self._add(
            edit_menu, "&Redo", self._app_model.objects.redo, ["Ctrl+Y", "Ctrl+Shift+Z"]
        )
        edit_menu.addSeparator()
        self._delete_action = self._add(
            edit_menu, "&Delete", self._app_model.objects.delete_selected, "Del"
        )
        edit_menu.addSeparator()
        self._settings_action = self._add(edit_menu, "Se&ttings...", self._settings_dialog)

        view_menu = self.addMenu("&View")
        self._add(view_menu, "Zoom &In", self._app_model.zoom_in, ["Ctrl++", "Ctrl+="])
        self._add(view_menu, "Zoom &Out", self._app_model.zoom_out, "Ctrl+-")

        simulation_menu = self.addMenu("&Simulation")
        # Space starts and stops it, see MainWindow.keyPressEvent(): shown, not a shortcut
        self._start_action = self._add(simulation_menu, "&Start\tSpace", self._start_stop)
        self._single_step_action = self._add(
            simulation_menu, "Single S&tep", self._app_model.model_single_step
        )
        self._reset_action = self._add(simulation_menu, "&Reset", self._app_model.model_reset)

        help_menu = self.addMenu("&Help")
        self._add(help_menu, "&Documentation", self._documentation, "F1")
        self._add(help_menu, "&About DigSim", self._about)

        self._app_model.sig_control_notify.connect(self.update_actions)
        self._app_model.sig_sim_time_notify.connect(self._sim_time_notify)
        self.update_actions()

    def _add(
        self,
        menu: QMenu,
        text: str,
        slot: Callable[[], object],
        shortcut: str | list[str] | None = None,
    ) -> QAction:
        action = QAction(text, self)
        if isinstance(shortcut, str):
            action.setShortcut(QKeySequence(shortcut))
        elif shortcut is not None:
            action.setShortcuts([QKeySequence(key) for key in shortcut])
        action.triggered.connect(lambda: slot())
        menu.addAction(action)
        # The shortcuts work also while the menu bar is hidden behind a dialog
        self._window.addAction(action)
        return action

    # File

    def new_circuit(self) -> None:
        """Clear the circuit, it can be undone"""
        self._app_model.clear_circuit()

    def open_circuit(self) -> None:
        """Ask for a circuit file and open it"""
        if self._app_model.is_changed and not are_you_sure_destroy_circuit(
            self._window, "Open circuit"
        ):
            return
        path, _ = QFileDialog.getOpenFileName(self, "Open Circuit", "", CIRCUIT_FILES)
        if path:
            self._app_model.load_circuit(path)

    def save_circuit(self) -> None:
        """Save the circuit in its file, or ask for one if it has none"""
        if self._app_model.circuit_path is None:
            self.save_circuit_as()
        else:
            self._app_model.save_circuit(self._app_model.circuit_path)

    def save_circuit_as(self) -> None:
        """Ask for a file and save the circuit in it"""
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Circuit", self._app_model.circuit_path or "", CIRCUIT_FILES
        )
        if path:
            self._app_model.save_circuit(path)

    # Edit

    def _settings_dialog(self) -> None:
        GuiSettingsDialog(self._window, self._app_model).start()

    def set_circuit_area(self, circuit_area: CircuitArea) -> None:
        """The circuit area, Delete follows its selection"""
        self._circuit_area = circuit_area
        circuit_area.scene().selectionChanged.connect(self.update_actions)

    # Simulation

    def _start_stop(self) -> None:
        if self._app_model.is_running:
            self._app_model.model_stop()
        else:
            self._app_model.model_start()

    def _sim_time_notify(self, time_s: float) -> None:
        self._time_s = time_s
        self.update_actions()

    # Help

    @staticmethod
    def _documentation() -> None:
        QDesktopServices.openUrl(QUrl(DOCUMENTATION_URL))

    def _about(self) -> None:
        QMessageBox.about(
            self._window,
            "About DigSim",
            f"<b>DigSim</b> v{self._package_version}<br>"
            "An interactive digital logic simulator<br><br>"
            f'<a href="{DOCUMENTATION_URL}">{DOCUMENTATION_URL}</a>',
        )

    def update_actions(self) -> None:
        """Turn the actions on and off for the state of the model"""
        running = self._app_model.is_running
        for action in (
            self._new_action,
            self._open_action,
            self._save_as_action,
            self._settings_action,
        ):
            action.setEnabled(not running)
        self._save_action.setEnabled(not running and self._app_model.is_changed)
        self._undo_action.setEnabled(not running and self._app_model.objects.can_undo())
        self._redo_action.setEnabled(not running and self._app_model.objects.can_redo())
        area = self._circuit_area
        has_selection = area is not None and area.has_selection()
        self._delete_action.setEnabled(not running and has_selection)
        self._start_action.setText("&Stop\tSpace" if running else "&Start\tSpace")
        self._single_step_action.setEnabled(not running)
        self._reset_action.setEnabled(not running and self._time_s > 0)
