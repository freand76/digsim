# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""The menu bar of the main window"""

from __future__ import annotations

import os
from collections.abc import Callable
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QSettings, QUrl, Signal
from PySide6.QtGui import QAction, QDesktopServices, QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QFileDialog, QMenu, QMenuBar, QMessageBox, QWidget

from digsim.app._clock_step import circuit_clocks
from digsim.app._recent_files import with_recent, without_file
from digsim.app.settings import GuiSettingsDialog

from ._circuit_area import CircuitArea


if TYPE_CHECKING:
    from digsim.app.model import AppModel

DOCUMENTATION_URL = "https://freand76.github.io/digsim/"
CIRCUIT_FILES = "Circuit Files (*.circuit);;All Files (*.*)"


class MenuBar(QMenuBar):
    """
    The menu bar: File, Edit, View, Simulation and Help. The actions that change the
    circuit are off while the simulation runs.
    """

    # Find Component: bring the component search to the front
    sig_find_component = Signal()
    # New Tab, Close Tab, and a circuit file to open (in its tab, see MainWindow.open_file)
    sig_new_tab = Signal()
    sig_close_tab = Signal()
    sig_open_file = Signal(str)

    def __init__(self, app_model: AppModel, parent: QWidget, package_version: str) -> None:
        super().__init__(parent)
        self._app_model = app_model
        self._window = parent
        self._package_version = package_version
        self._time_s: float = 0
        # The circuit area of the tab that is shown, see set_tab()
        self._circuit_area: CircuitArea | None = None
        self._can_paste = False
        # The tab that is shown is a view of a subcircuit, see set_tab()
        self._read_only = False
        # The circuit file of each model when the recent files were last updated
        self._recent_paths: dict[AppModel, str | None] = {}

        file_menu = self.addMenu("&File")
        self._add(file_menu, "New &Tab", self.sig_new_tab.emit, "Ctrl+T")
        self._new_action = self._add(file_menu, "&New", self.new_circuit, "Ctrl+N")
        self._open_action = self._add(file_menu, "&Open...", self.open_circuit, "Ctrl+O")
        self._recent_menu = file_menu.addMenu("Open &Recent")
        self._recent_menu.aboutToShow.connect(self._fill_recent_menu)
        self._save_action = self._add(file_menu, "&Save", self.save_circuit, "Ctrl+S")
        self._save_as_action = self._add(
            file_menu, "Save &As...", self.save_circuit_as, "Ctrl+Shift+S"
        )
        file_menu.addSeparator()
        self._export_action = self._add(file_menu, "&Export Image...", self.export_image, "Ctrl+E")
        file_menu.addSeparator()
        self._add(file_menu, "&Close Tab", self.sig_close_tab.emit, "Ctrl+W")
        self._add(file_menu, "&Quit", parent.close, "Ctrl+Q")

        edit_menu = self.addMenu("&Edit")
        # The model of the tab that is shown when the action is triggered
        self._undo_action = self._add(
            edit_menu, "&Undo", lambda: self._app_model.objects.undo(), "Ctrl+Z"
        )
        self._redo_action = self._add(
            edit_menu,
            "&Redo",
            lambda: self._app_model.objects.redo(),
            ["Ctrl+Y", "Ctrl+Shift+Z"],
        )
        edit_menu.addSeparator()
        self._cut_action = self._add(edit_menu, "Cu&t", self._area_call("cut_selection"), "Ctrl+X")
        self._copy_action = self._add(
            edit_menu, "&Copy", self._area_call("copy_selection"), "Ctrl+C"
        )
        self._paste_action = self._add(edit_menu, "&Paste", self._area_call("paste"), "Ctrl+V")
        self._duplicate_action = self._add(
            edit_menu, "D&uplicate", self._area_call("duplicate_selection"), "Ctrl+D"
        )
        # Cut, Copy and Duplicate are off without selected components, and so are their
        # shortcuts: these tell why nothing is copied then (a wire alone is not copied)
        self._nothing_to_copy = [
            QShortcut(QKeySequence(key), parent, self._show_nothing_to_copy)
            for key in ("Ctrl+X", "Ctrl+C", "Ctrl+D")
        ]
        self._delete_action = self._add(
            edit_menu, "&Delete", lambda: self._app_model.objects.delete_selected(), "Del"
        )
        self._rotate_action = self._add(edit_menu, "&Rotate", self._rotate, "Ctrl+R")
        self._flip_horizontal_action = self._add(
            edit_menu, "Flip &Horizontal", lambda: self._flip(True), "Ctrl+Shift+H"
        )
        self._flip_vertical_action = self._add(
            edit_menu, "Flip &Vertical", lambda: self._flip(False), "Ctrl+Shift+V"
        )
        edit_menu.addSeparator()
        self._find_action = self._add(
            edit_menu, "&Find Component...", self.sig_find_component.emit, ["Ctrl+K", "Ctrl+F"]
        )
        edit_menu.addSeparator()
        self._settings_action = self._add(edit_menu, "Se&ttings...", self._settings_dialog)

        view_menu = self.addMenu("&View")
        self._add(view_menu, "Zoom &In", lambda: self._app_model.zoom_in(), ["Ctrl++", "Ctrl+="])
        self._add(view_menu, "Zoom &Out", lambda: self._app_model.zoom_out(), "Ctrl+-")
        self._add(
            view_menu, "Zoom to &Fit", lambda: self._app_model.zoom_fit(), ["Ctrl+0", "Home"]
        )
        view_menu.addSeparator()
        self._view_menu = view_menu

        simulation_menu = self.addMenu("&Simulation")
        # Space starts and stops it, see MainWindow.keyPressEvent(): shown, not a shortcut
        self._start_action = self._add(simulation_menu, "&Start\tSpace", self._start_stop)
        self._single_step_action = self._add(
            simulation_menu, "Single S&tep", lambda: self._app_model.model_single_step()
        )
        self._clock_step_action = self._add(
            simulation_menu, "Step &Clock", lambda: self._app_model.model_clock_step(), "F10"
        )
        self._reset_action = self._add(
            simulation_menu, "&Reset", lambda: self._app_model.model_reset()
        )

        help_menu = self.addMenu("&Help")
        self._add(help_menu, "&Documentation", self._documentation, "F1")
        self._add(help_menu, "&About DigSim", self._about)

        self._app_model.sig_control_notify.connect(self.update_actions)
        self._app_model.sig_sim_time_notify.connect(self._sim_time_notify)
        QApplication.clipboard().dataChanged.connect(self._clipboard_changed)
        self._clipboard_changed()

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
        """Ask for a circuit file and open it, in a tab of its own (see sig_open_file)"""
        path, _ = QFileDialog.getOpenFileName(self, "Open Circuit", "", CIRCUIT_FILES)
        if path:
            self.sig_open_file.emit(path)

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

    @staticmethod
    def settings() -> QSettings:
        """
        The settings of the application, like the recent files. DIGSIM_SETTINGS_DIR sets
        another folder for them, like scripts and tests do.
        """
        folder = os.environ.get("DIGSIM_SETTINGS_DIR")
        if folder:
            return QSettings(str(Path(folder) / "digsim.ini"), QSettings.Format.IniFormat)
        return QSettings(QSettings.Format.IniFormat, QSettings.Scope.UserScope, "digsim", "digsim")

    def recent_files(self) -> list[str]:
        """The circuit files opened or saved last, the last one first"""
        value = self.settings().value("recent_files", [])
        # A list of one is read back as a string
        if isinstance(value, str):
            return [value]
        return [str(path) for path in value] if isinstance(value, list) else []

    def _set_recent_files(self, paths: list[str]) -> None:
        self.settings().setValue("recent_files", paths)
        self._recent_menu.setEnabled(bool(paths) and not self._app_model.is_running)

    def _fill_recent_menu(self) -> None:
        self._recent_menu.clear()
        for number, path in enumerate(self.recent_files(), start=1):
            action = self._recent_menu.addAction(f"&{number} {path}")
            action.triggered.connect(partial(self.open_recent, path))
        self._recent_menu.addSeparator()
        self._recent_menu.addAction("&Clear Recent Files").triggered.connect(
            lambda: self._set_recent_files([])
        )

    def open_recent(self, path: str) -> None:
        """Open a recent circuit file, it leaves the list if it is gone"""
        if not Path(path).is_file():
            self._set_recent_files(without_file(self.recent_files(), path))
            self._app_model.sig_error.emit(f"Could not open {path}: the file is gone")
            return
        self.sig_open_file.emit(path)

    def export_image(self) -> None:
        """Ask for a file and save the circuit as an image in it, PNG or SVG"""
        if self._circuit_area is None:
            return
        circuit_path = self._app_model.circuit_path
        default = str(Path(circuit_path).with_suffix(".png")) if circuit_path else "circuit.png"
        path, chosen = QFileDialog.getSaveFileName(
            self, "Export Image", default, "PNG Image (*.png);;SVG Image (*.svg)"
        )
        if not path:
            return
        if not path.lower().endswith((".png", ".svg")):
            path += ".svg" if "svg" in chosen.lower() else ".png"
        try:
            self._circuit_area.export_image(path)
        except (ValueError, OSError) as exc:
            self._app_model.sig_error.emit(f"Could not export the image: {exc!s}")

    # Edit

    def _settings_dialog(self) -> None:
        GuiSettingsDialog(self._window, self._app_model).start()

    def set_tab(
        self, app_model: AppModel, circuit_area: CircuitArea, read_only: bool = False
    ) -> None:
        """
        The model and the circuit area of the tab that is shown, that the actions work
        on. Delete and Copy follow the selection of the circuit area, Paste the clipboard.
        A read-only tab (the view of a subcircuit) has no actions that edit the circuit.
        """
        self._read_only = read_only
        if app_model is not self._app_model:
            self._app_model.sig_control_notify.disconnect(self.update_actions)
            self._app_model.sig_sim_time_notify.disconnect(self._sim_time_notify)
            app_model.sig_control_notify.connect(self.update_actions)
            app_model.sig_sim_time_notify.connect(self._sim_time_notify)
            self._app_model = app_model
            self._time_s = app_model.objects.circuit.time_ns / 1000000000
        if circuit_area is not self._circuit_area:
            if self._circuit_area is not None:
                self._circuit_area.scene().selectionChanged.disconnect(self.update_actions)
            circuit_area.scene().selectionChanged.connect(self.update_actions)
            self._circuit_area = circuit_area
        self.update_actions()

    def _area_call(self, method: str) -> Callable[[], None]:
        """A method of the circuit area, for an action"""

        def call() -> None:
            if self._circuit_area is not None:
                getattr(self._circuit_area, method)()

        return call

    def add_view_menu(self, title: str) -> QMenu:
        """A submenu of the View menu"""
        return self._view_menu.addMenu(title)

    def add_pane_action(self, action: QAction) -> None:
        """An action that shows or hides a pane of the window, in the View menu"""
        self._view_menu.addAction(action)

    def _rotate(self) -> None:
        if self._circuit_area is not None:
            selected = self._circuit_area.selected_objects()
            self._app_model.objects.components.rotate(selected)

    def _flip(self, horizontal: bool) -> None:
        if self._circuit_area is not None:
            selected = self._circuit_area.selected_objects()
            self._app_model.objects.components.flip(selected, horizontal)

    def _show_nothing_to_copy(self) -> None:
        if self._circuit_area is not None:
            self._circuit_area.show_message(
                "Nothing to copy: select components, the wires between them are copied with them"
            )

    def _clipboard_changed(self) -> None:
        self._can_paste = CircuitArea.clipboard_data() is not None
        self.update_actions()

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
        # A circuit that was opened or saved is a recent file
        path = self._app_model.circuit_path
        if path is not None and path != self._recent_paths.get(self._app_model):
            self._set_recent_files(with_recent(self.recent_files(), path))
        self._recent_paths[self._app_model] = path
        self._recent_menu.setEnabled(not running and bool(self.recent_files()))
        self._export_action.setEnabled(
            not running and not self._app_model.objects.components.is_empty()
        )
        for action in (
            self._new_action,
            self._open_action,
            self._save_as_action,
            self._find_action,
            self._settings_action,
        ):
            action.setEnabled(not running)
        self._save_action.setEnabled(not running and self._app_model.is_changed)
        self._undo_action.setEnabled(not running and self._app_model.objects.can_undo())
        self._redo_action.setEnabled(not running and self._app_model.objects.can_redo())
        area = self._circuit_area
        has_selection = area is not None and area.has_selection()
        has_components = area is not None and bool(area.selected_objects())
        self._delete_action.setEnabled(not running and has_selection)
        can_turn = (
            not running
            and area is not None
            and any(obj.ROTATABLE for obj in area.selected_objects())
        )
        for action in (
            self._rotate_action,
            self._flip_horizontal_action,
            self._flip_vertical_action,
        ):
            action.setEnabled(can_turn)
        for action in (self._cut_action, self._copy_action, self._duplicate_action):
            action.setEnabled(not running and has_components)
        # Their shortcuts say why nothing happens instead
        for shortcut in self._nothing_to_copy:
            shortcut.setEnabled(area is not None and not running and not has_components)
        self._paste_action.setEnabled(not running and self._can_paste)
        self._start_action.setText("&Stop\tSpace" if running else "&Start\tSpace")
        self._single_step_action.setEnabled(not running)
        self._clock_step_action.setEnabled(
            not running and bool(circuit_clocks(self._app_model.objects.circuit))
        )
        self._reset_action.setEnabled(not running and self._time_s > 0)
        if self._read_only:
            for action in (
                self._new_action,
                self._undo_action,
                self._redo_action,
                self._cut_action,
                self._copy_action,
                self._paste_action,
                self._duplicate_action,
                self._delete_action,
                self._rotate_action,
                self._flip_horizontal_action,
                self._flip_vertical_action,
                self._find_action,
                self._settings_action,
                self._export_action,
            ):
                action.setEnabled(False)
            for shortcut in self._nothing_to_copy:
                shortcut.setEnabled(False)
