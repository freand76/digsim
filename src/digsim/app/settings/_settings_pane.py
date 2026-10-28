# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""The settings pane: the settings of the selected component, beside the circuit"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from digsim.app._settings_values import changes, pane_parameters, pane_values
from digsim.app.gui_objects import ComponentObject
from digsim.app.gui_objects import _theme as theme

from ._component_settings import (
    _SETTINGS_WIDGETS,
    ComponentSettingsBase,
    ComponentSettingSingleLineText,
)


if TYPE_CHECKING:
    from PySide6.QtWidgets import QGraphicsView

    from digsim.app.model import AppModel


class ComponentSettingsPane(QWidget):
    """
    The settings of the component that is selected, with an input for each, like the
    settings dialog has. Apply changes them, an undo step: a setting that changes the
    ports builds the component again (see ModelComponents.change_settings). The pane
    follows the circuit of the tab that is shown.
    """

    sig_value_updated = Signal(str)
    # An input's parameter, and whether its value is valid
    sig_enable_ok = Signal(str, bool)

    def __init__(self, parent: QWidget | None) -> None:
        super().__init__(parent)
        self._app_model: AppModel | None = None
        self._area: QGraphicsView | None = None
        self._read_only = False
        self._object: ComponentObject | None = None
        # The values the component has, and the ones in the inputs
        self._values: dict[str, Any] = {}
        self._settings: dict[str, Any] = {}
        self._inputs: list[ComponentSettingsBase] = []

        layout = QVBoxLayout(self)
        self._title = QLabel(self)
        self._title.setFont(theme.font(10, bold=True))
        layout.addWidget(self._title)
        self._hint = QLabel(self)
        self._hint.setWordWrap(True)
        layout.addWidget(self._hint)
        self._form = QVBoxLayout()
        layout.addLayout(self._form)
        layout.addStretch(1)
        buttons = QHBoxLayout()
        self._reset_button = QPushButton("Reset", self)
        self._reset_button.setToolTip("Show the settings the component has")
        self._reset_button.clicked.connect(lambda: self.refresh(force=True))
        self._apply_button = QPushButton("Apply", self)
        self._apply_button.setToolTip("Change the component to these settings")
        self._apply_button.setDefault(True)
        self._apply_button.clicked.connect(self.accept)
        buttons.addWidget(self._reset_button)
        buttons.addWidget(self._apply_button)
        layout.addLayout(buttons)
        # The parameters whose inputs have a value that isn't valid
        self._invalid: set[str] = set()
        self.sig_enable_ok.connect(self._input_valid)
        self.refresh()

    def set_tab(self, app_model: AppModel, area: QGraphicsView, read_only: bool) -> None:
        """The model and the circuit area of the tab that is shown"""
        if self._app_model is not None and self._app_model is not app_model:
            self._app_model.sig_control_notify.disconnect(self.refresh)
            self._app_model.sig_synchronize_gui.disconnect(self.refresh)
        if self._area is not None and self._area is not area:
            self._area.scene().selectionChanged.disconnect(self.refresh)
        if self._app_model is not app_model:
            app_model.sig_control_notify.connect(self.refresh)
            app_model.sig_synchronize_gui.connect(self.refresh)
        if self._area is not area:
            area.scene().selectionChanged.connect(self.refresh)
        self._app_model, self._area, self._read_only = app_model, area, read_only
        self.refresh()

    def _selected(self) -> ComponentObject | None:
        """The component that is selected, if one is (and the circuit can change)"""
        if self._app_model is None or self._area is None or self._read_only:
            return None
        if self._app_model.is_running:
            return None
        selected = [
            item
            for item in self._area.scene().selectedItems()
            if isinstance(item, ComponentObject)
        ]
        return selected[0] if len(selected) == 1 else None

    def refresh(self, force: bool = False) -> None:
        """
        Show the settings of the selected component, as it has them. The inputs stay as
        they are while the same component is selected, unless 'force'.
        """
        selected = self._selected()
        if selected is not None and selected is self._object and not force:
            return
        for item in self._inputs:
            self._form.removeWidget(item)
            item.deleteLater()
        self._inputs = []
        self._invalid = set()
        self._object = selected
        if self._object is None:
            self._title.setText("Settings")
            running = self._app_model is not None and self._app_model.is_running
            self._hint.setText(
                "Not while the simulation runs"
                if running
                else "Select a component to see its settings"
            )
            self._hint.show()
            self._apply_button.setEnabled(False)
            self._reset_button.setEnabled(False)
            return
        assert self._app_model is not None
        component = self._object.component
        parameters = pane_parameters(component, self._app_model.objects.circuit)
        self._values = pane_values(parameters)
        self._settings = dict(self._values)
        self._title.setText(component.display_name())
        self._hint.setText("" if parameters else "No settings")
        self._hint.setVisible(not parameters)
        for name, parameter in parameters.items():
            kind = parameter["type"]
            if kind == "str" and parameter.get("single_line", False):
                widget_class: type[ComponentSettingsBase] = ComponentSettingSingleLineText
            else:
                widget_class = _SETTINGS_WIDGETS[kind]
            item = widget_class(self, name, parameter, self._settings)
            self._form.addWidget(item)
            self._inputs.append(item)
        self._apply_button.setEnabled(bool(parameters) and not self._invalid)
        self._reset_button.setEnabled(bool(parameters))

    def _input_valid(self, parameter: str, valid: bool) -> None:
        """Apply is on while the values of all the inputs are valid"""
        if valid:
            self._invalid.discard(parameter)
        else:
            self._invalid.add(parameter)
        self._apply_button.setEnabled(self._object is not None and not self._invalid)

    def accept(self) -> None:
        """Apply: give the component the settings of the inputs"""
        if self._object is None or self._app_model is None:
            return
        changed = changes(self._values, self._settings)
        if not changed:
            return
        component_object = self._app_model.objects.components.change_settings(
            self._object, changed
        )
        if component_object is not None:
            # Built again, the component has a new object
            if self._area is not None:
                self._area.scene().clearSelection()
            component_object.setSelected(True)
        self.refresh(force=True)
        self._title.setFocus(Qt.FocusReason.OtherFocusReason)
