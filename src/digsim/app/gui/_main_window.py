# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""The main window and widgets of the digsim gui application"""

from __future__ import annotations

from functools import partial
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import (
    QActionGroup,
    QCloseEvent,
    QGuiApplication,
    QKeyEvent,
    QKeySequence,
    QShowEvent,
)
from PySide6.QtWidgets import (
    QApplication,
    QDockWidget,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from digsim.app._app_settings import simulate_hidden_tabs
from digsim.app._yosys_interface import same_file
from digsim.app.editor import VerilogEditors
from digsim.app.gui_objects._subcircuit_object import reload_subcircuits
from digsim.app.model import AppModel
from digsim.app.settings._settings_pane import ComponentSettingsPane
from digsim.circuit.components import SubCircuit
from digsim.circuit.components._subcircuit import files_used

from ._appearance import THEMES, apply_theme
from ._circuit_area import CircuitArea
from ._component_search import ComponentSearch
from ._component_selection import ComponentSelection
from ._menu_bar import MenuBar
from ._subcircuit_view import SubCircuitView, ViewTab
from ._top_bar import TopBar
from ._utils import are_you_sure_destroy_circuit
from ._warning_dialog import WarningDialog


# The setting that remembers if the settings pane is shown, it is hidden until the user
# shows it. The old key has "shown" in every installation from when it was shown at first.
SETTINGS_PANE_KEY = "window/settings_pane_shown"
OLD_SETTINGS_PANE_KEY = "window/settings_pane"
# The setting with the theme, see THEMES
THEME_KEY = "window/theme"


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

        # The component search above the component selection
        self._selection_column = QWidget(self)
        self._selection_column.setFixedWidth(106)
        column_layout = QVBoxLayout(self._selection_column)
        column_layout.setContentsMargins(0, 0, 0, 0)
        column_layout.setSpacing(4)

        self._selection_area = QScrollArea(self)
        self._selection_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self._selection_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._circuit_area = CircuitArea(app_model, self)
        selection_panel = ComponentSelection(self._circuit_area, self)
        self._component_search = ComponentSearch(self._circuit_area, self, self)

        self._selection_area.setWidget(selection_panel)
        column_layout.addWidget(self._component_search)
        column_layout.addWidget(self._selection_area, 1)

        layout.addWidget(self._selection_column)
        layout.addWidget(self._circuit_area, 1)
        self._circuit_area.setFocus()

    def _control_notify(self) -> None:
        self._selection_column.setEnabled(not self._app_model.is_running)

    def focus_component_search(self) -> None:
        """Bring the component search to the front, to type the component to add"""
        if not self._app_model.is_running:
            self._component_search.focus_search()

    @property
    def circuit_area(self) -> CircuitArea:
        """Get the circuit area"""
        return self._circuit_area


class CircuitTab(QWidget):
    """
    A tab of the main window: a circuit, with its model, its top bar, its circuit editor
    and its Verilog editors
    """

    def __init__(self, app_model: AppModel, window: QWidget) -> None:
        super().__init__(window)
        self.app_model = app_model

        layout = QVBoxLayout(self)
        self.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.circuit_editor = CircuitEditor(app_model, self)
        top_bar = TopBar(app_model, self)
        self.vcd = top_bar.vcd
        layout.addWidget(top_bar)
        layout.setStretchFactor(top_bar, 0)

        layout.addWidget(self.circuit_editor)
        layout.setStretchFactor(self.circuit_editor, 1)

        # The editors of the Verilog files of the tab's Yosys components
        self.verilog_editors = VerilogEditors(app_model, window)
        app_model.sig_edit_verilog.connect(self.verilog_editors.open)
        app_model.sig_yosys_updated.connect(self.verilog_editors.components_updated)

    @property
    def circuit_area(self) -> CircuitArea:
        """The circuit area of the tab"""
        return self.circuit_editor.circuit_area

    def is_unused(self) -> bool:
        """A new tab that nothing was done in, a file can be opened in it"""
        model = self.app_model
        return (
            model.objects.components.is_empty()
            and not model.is_changed
            and model.circuit_path is None
            and not model.objects.can_undo()
        )

    def title(self) -> str:
        """The name of the circuit's file, with a '*' when it has changed since"""
        path = self.app_model.circuit_path
        name = Path(path).name if path is not None else "Untitled"
        return f"{name}{'*' if self.app_model.is_changed else ''}"


class MainWindow(QMainWindow):
    """
    The main window for the application: a circuit in each tab. The tab bar is shown
    when there are two tabs or more.
    """

    def __init__(self, app_model: AppModel, package_version: str) -> None:
        super().__init__()

        self._package_version = package_version
        self.resize(1280, 720)
        self._menu_bar = MenuBar(app_model, self, package_version)
        self.setMenuBar(self._menu_bar)
        self._menu_bar.sig_new_tab.connect(self.new_tab)
        self._menu_bar.sig_close_tab.connect(self.close_current_tab)
        self._menu_bar.sig_open_file.connect(self.open_file)
        self._menu_bar.sig_find_component.connect(self._find_component)
        self._menu_bar.sig_app_settings_changed.connect(self._app_settings_changed)
        self._tabs = QTabWidget(self)
        self._tabs.setDocumentMode(True)
        self._tabs.setTabsClosable(True)
        self._tabs.setMovable(True)
        self._tabs.setTabBarAutoHide(True)
        self._tabs.tabCloseRequested.connect(self._close_tab_at)
        self._tabs.currentChanged.connect(self._tab_changed)
        self.setCentralWidget(self._tabs)
        self._add_settings_pane()
        self._add_theme_menu()
        # The tab that was shown last, its simulation stops when another one is shown
        self._shown_tab: CircuitTab | ViewTab | None = None
        self.setAcceptDrops(True)  # Needed to avoid "No drag target set."
        self.add_tab(app_model)
        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self._about_to_quit)

    def _about_to_quit(self) -> None:
        """
        The scenes stop telling the menu bar and the settings pane that the selection
        changed: when the application is torn down, a scene deletes its selected items
        after the objects that the menu bar and the settings pane use are deleted
        """
        for tab in self.tabs():
            tab.circuit_area.scene().blockSignals(True)

    def _add_settings_pane(self) -> None:
        """
        The settings pane, to the right of the circuit: the settings of the selected
        component. It is hidden until View > Settings Pane (F4) or Settings in the context
        menu of a component shows it, and View > Settings Pane hides it again. That is
        remembered.
        """
        self.settings_pane = ComponentSettingsPane(self)
        scroll = QScrollArea(self)
        scroll.setWidget(self.settings_pane)
        scroll.setWidgetResizable(True)
        # The inputs fit the width, their texts wrap
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.settings_dock = QDockWidget("Settings", self)
        self.settings_dock.setObjectName("settings_pane")
        self.settings_dock.setWidget(scroll)
        self.settings_dock.setMinimumWidth(220)
        self.settings_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetClosable
            | QDockWidget.DockWidgetFeature.DockWidgetMovable
        )
        self.settings_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.settings_dock)
        self._pane_sized = False
        action = self.settings_dock.toggleViewAction()
        action.setText("&Settings Pane")
        action.setShortcut(QKeySequence("F4"))
        self.addAction(action)
        self._menu_bar.add_pane_action(action)
        MenuBar.settings().remove(OLD_SETTINGS_PANE_KEY)
        shown = MenuBar.settings().value(SETTINGS_PANE_KEY, False, type=bool)
        self.settings_dock.setVisible(bool(shown))
        # When the user shows or hides it, and when the window closes (it is hidden then,
        # see closeEvent())
        action.triggered.connect(
            lambda visible: MenuBar.settings().setValue(SETTINGS_PANE_KEY, visible)
        )

    def _add_theme_menu(self) -> None:
        """
        View > Theme: as the system has it (the default), light or dark. It is remembered,
        and used from the start: the circuit areas get its colors when they are made.
        """
        choice = str(MenuBar.settings().value(THEME_KEY, "system"))
        if choice not in THEMES:
            choice = "system"
        self._theme = choice
        apply_theme(choice)
        menu = self._menu_bar.add_view_menu("&Theme")
        group = QActionGroup(self)
        for name, text in THEMES.items():
            action = menu.addAction(text)
            action.setCheckable(True)
            action.setChecked(name == choice)
            action.setData(name)
            group.addAction(action)
        group.triggered.connect(lambda action: self.set_theme(str(action.data())))
        # The system's color scheme can change while the application runs
        QGuiApplication.styleHints().colorSchemeChanged.connect(self._system_theme_changed)

    def set_theme(self, choice: str) -> None:
        """Use a theme (see THEMES), and remember it"""
        self._theme = choice
        MenuBar.settings().setValue(THEME_KEY, choice)
        apply_theme(choice)
        self._refresh_theme()

    def _system_theme_changed(self) -> None:
        if self._theme == "system":
            apply_theme("system")
            self._refresh_theme()

    def _refresh_theme(self) -> None:
        """Paint everything again in the colors of the theme"""
        for area in self.findChildren(CircuitArea):
            area.refresh_theme()
        for view in self.findChildren(SubCircuitView):
            view.refresh_theme()
        for widget in self.findChildren(QWidget):
            widget.update()

    def showEvent(self, event: QShowEvent) -> None:
        """QT event callback function"""
        super().showEvent(event)
        if not self._pane_sized:
            # Wide enough for the inputs, like the dialog had them (once it is shown, Qt
            # doesn't size docks before)
            self._pane_sized = True
            self.resizeDocks([self.settings_dock], [340], Qt.Orientation.Horizontal)

    def show_settings_pane(self) -> None:
        """Show the settings pane, like Settings in the context menu of a component does"""
        self.settings_dock.show()
        self.settings_dock.raise_()

    # The tabs

    def tabs(self) -> list[CircuitTab]:
        """The tabs with circuits, from left to right (not the views of subcircuits)"""
        return [tab for tab in self._all_tabs() if isinstance(tab, CircuitTab)]

    def _all_tabs(self) -> list[CircuitTab | ViewTab]:
        tabs = []
        for index in range(self._tabs.count()):
            tab = self._tabs.widget(index)
            assert isinstance(tab, (CircuitTab, ViewTab))
            tabs.append(tab)
        return tabs

    def current_tab(self) -> CircuitTab:
        """The circuit tab that is shown, or the one of the subcircuit view that is shown"""
        tab = self._tabs.currentWidget()
        if isinstance(tab, ViewTab):
            tab = tab.parent_tab
        assert isinstance(tab, CircuitTab)
        return tab

    def view_tabs(self) -> list[ViewTab]:
        """The tabs with views of subcircuits"""
        return [tab for tab in self._all_tabs() if isinstance(tab, ViewTab)]

    def open_view(self, app_model: AppModel, names: list[str]) -> None:
        """
        View Subcircuit: show the view of a subcircuit instance (by its chain of names),
        a new tab if it isn't open
        """
        for view in self.view_tabs():
            if view.app_model is app_model and view.names == names:
                self._tabs.setCurrentWidget(view)
                return
        parent_tab = next(tab for tab in self.tabs() if tab.app_model is app_model)
        view = ViewTab(app_model, names, parent_tab, self.open_view, self)
        index = self._tabs.addTab(view, view.title())
        self._tabs.setTabToolTip(index, f"{view.title()}, read-only")
        self._tabs.setCurrentIndex(index)

    @property
    def _app_model(self) -> AppModel:
        """The model of the tab that is shown"""
        return self.current_tab().app_model

    @property
    def verilog_editors(self) -> VerilogEditors:
        """The Verilog editors of the tab that is shown"""
        return self.current_tab().verilog_editors

    def add_tab(self, app_model: AppModel | None = None) -> CircuitTab:
        """Add a tab with a new circuit (or the circuit of a model), and show it"""
        if app_model is None:
            app_model = AppModel()
        tab = CircuitTab(app_model, self)
        app_model.sig_error.connect(self.error_dialog)
        app_model.sig_warning_log.connect(self.warning_log_dialog)
        app_model.sig_control_notify.connect(partial(self._update_titles, tab))
        app_model.sig_edit_subcircuit.connect(self.open_file)
        app_model.sig_view_subcircuit.connect(lambda name: self.open_view(app_model, [name]))
        app_model.sig_show_settings.connect(self.show_settings_pane)
        app_model.sig_saved.connect(partial(self._circuit_saved, tab))
        index = self._tabs.addTab(tab, tab.title())
        self._tabs.setCurrentIndex(index)
        self._update_titles(tab)
        return tab

    def new_tab(self) -> None:
        """File > New Tab: an empty circuit in a new tab"""
        self.add_tab()

    def open_file(self, path: str) -> None:
        """
        Open a circuit file: show its tab if it is open, else load it in the tab that is
        shown if that is unused, or in a new tab
        """
        for tab in self.tabs():
            open_path = tab.app_model.circuit_path
            if open_path is not None and Path(open_path).resolve() == Path(path).resolve():
                self._tabs.setCurrentWidget(tab)
                return
        tab = self.current_tab()
        if not tab.is_unused():
            tab = self.add_tab()
        tab.app_model.load_circuit(path)
        if tab.app_model.circuit_path is None:
            if len(self.tabs()) > 1 and tab.is_unused():
                # The file couldn't be loaded (the model said why), the new tab goes again
                self._remove_tab(tab)
            return
        # The whole circuit, once the view has its size (a new tab is laid out first)
        QTimer.singleShot(0, tab.app_model.zoom_fit)

    def close_current_tab(self) -> None:
        """File > Close Tab"""
        self._close_tab_at(self._tabs.currentIndex())

    def _close_view(self, view: ViewTab) -> None:
        if self._shown_tab is view:
            self._shown_tab = None
        self._tabs.removeTab(self._tabs.indexOf(view))
        view.deleteLater()

    def _close_tab_at(self, index: int) -> bool:
        """
        Close a tab, asking first if its circuit has changed, False if that was cancelled.
        The last tab is not closed, it gets an empty circuit.
        """
        tab = self._tabs.widget(index)
        if isinstance(tab, ViewTab):
            self._close_view(tab)
            return True
        assert isinstance(tab, CircuitTab)
        if not tab.verilog_editors.close_all():
            return False
        if tab.app_model.is_changed and not are_you_sure_destroy_circuit(
            self, f"Close {tab.title()}"
        ):
            return False
        if len(self.tabs()) == 1:
            self.add_tab()
        self._remove_tab(tab)
        return True

    def _remove_tab(self, tab: CircuitTab) -> None:
        # Its views go with it
        for view in self.view_tabs():
            if view.parent_tab is tab:
                self._close_view(view)
        tab.app_model.model_stop()
        if self._shown_tab is tab:
            self._shown_tab = None
        self._tabs.removeTab(self._tabs.indexOf(tab))
        tab.deleteLater()
        # Then the model is freed, with its circuit
        tab.app_model.disconnect_signals()

    def _app_settings_changed(self) -> None:
        """Simulations in hidden tabs turned off: the hidden tabs stop"""
        if simulate_hidden_tabs():
            return
        shown = self.current_tab().app_model
        for tab in self.tabs():
            if tab.app_model is not shown:
                tab.app_model.model_stop()

    def _tab_changed(self, _: int) -> None:
        """
        Another tab is shown: the one that was shown stops (or goes on without sound, see
        simulate_hidden_tabs()), the menu follows the new one
        """
        if self._tabs.count() == 0:
            return
        shown = self._tabs.currentWidget()
        assert isinstance(shown, (CircuitTab, ViewTab))
        tab = self.current_tab()
        # A view of a subcircuit shows the simulation of its circuit, which goes on
        if (
            self._shown_tab is not None
            and self._shown_tab.app_model is not shown.app_model
            and not simulate_hidden_tabs()
        ):
            self._shown_tab.app_model.model_stop()
        for circuit_tab in self.tabs():
            circuit_tab.circuit_area.set_muted(circuit_tab is not tab)
        self._shown_tab = shown
        view = shown.view if isinstance(shown, ViewTab) else None
        self._menu_bar.set_tab(tab.app_model, tab.circuit_area, view)
        self._menu_bar.set_vcd(tab.vcd)
        self.settings_pane.set_tab(tab.app_model, tab.circuit_area, isinstance(shown, ViewTab))
        self._update_titles(tab)

    def _circuit_saved(self, saved_tab: CircuitTab, path: str) -> None:
        """
        A circuit was saved: the subcircuits in the other tabs that use its file, also
        through their own subcircuits, are built again from their files
        """
        for tab in self.tabs():
            if tab is saved_tab:
                continue
            files = {
                str(subcircuit.source_file())
                for subcircuit in tab.app_model.objects.circuit.get_toplevel_components()
                if isinstance(subcircuit, SubCircuit)
            }
            for file in sorted(files):
                if same_file(file, path) or Path(path).resolve() in files_used(file):
                    reload_subcircuits(self, tab.app_model, file)

    def _find_component(self) -> None:
        self.current_tab().circuit_editor.focus_component_search()

    def _update_titles(self, tab: CircuitTab) -> None:
        """
        The title of a tab, and the title of the window, with the file of the circuit that
        is shown, with a '*' when it has changed since
        """
        index = self._tabs.indexOf(tab)
        if index < 0:
            return
        # A tab that simulates is marked, the hidden ones too (see simulate_hidden_tabs())
        running = "\u25b6 " if tab.app_model.is_running else ""
        self._tabs.setTabText(index, f"{running}{tab.title()}")
        path = tab.app_model.circuit_path
        self._tabs.setTabToolTip(index, path or "")
        if tab is not self._tabs.currentWidget():
            return
        title = f"DigSim - Interactive Digital Logic Simulator [v{self._package_version}]"
        if path is not None:
            title += f" - {tab.title()}"
        self.setWindowTitle(title)

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
        tabs = self.tabs()
        if not all(tab.verilog_editors.close_all() for tab in tabs):
            event.ignore()
            return
        changed = [tab for tab in tabs if tab.app_model.is_changed]
        if not changed or are_you_sure_destroy_circuit(self, "Close Application"):
            # Also when its own close button hid it
            MenuBar.settings().setValue(SETTINGS_PANE_KEY, self.settings_dock.isVisible())
            # Stops the simulation threads and waits for them
            for tab in tabs:
                tab.app_model.model_stop()
            super().closeEvent(event)
        else:
            event.ignore()
