# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""The component settings dialog(s)"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QEvent, QObject, Qt, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSlider,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from digsim.app._ic_search import search_ics
from digsim.circuit.components import IntegratedCircuit
from digsim.circuit.components.atoms import Parameter


if TYPE_CHECKING:
    from digsim.app.model import AppModel


class ComponentSettingsException(Exception):
    """ComponentSettingsException"""


class ComponentSettingsBase(QFrame):
    """The base class for the input of one parameter in the settings dialog"""

    def __init__(
        self,
        parent: ComponentSettingsDialog,
        parameter: str,
        parameter_dict: Parameter,
        settings: dict[str, Any],
    ) -> None:
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.Panel)
        self._parent = parent
        self._parameter = parameter
        self._parameter_dict = parameter_dict
        self._settings = settings
        self._parent.sig_value_updated.connect(self._on_setting_change)

    def emit_signal(self) -> None:
        """Signal other settings components that a value has changed"""
        self._parent.sig_value_updated.emit(self._parameter)

    def _on_setting_change(self, parameter: str) -> None:
        if parameter != self._parameter:
            self.on_setting_change(parameter)

    def on_setting_change(self, parameter: str) -> None:
        """Called when other setting is changed"""


class ComponentSettingText(ComponentSettingsBase):
    """Text setting, in a text box with several lines"""

    def __init__(
        self,
        parent: ComponentSettingsDialog,
        parameter: str,
        parameter_dict: Parameter,
        settings: dict[str, Any],
    ) -> None:
        super().__init__(parent, parameter, parameter_dict, settings)
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        layout.addWidget(QLabel(self._parameter_dict["description"]))
        self._text_edit = QTextEdit(self)
        self._text_edit.setText(self._parameter_dict["default"])
        self._text_edit.textChanged.connect(self._update)
        layout.addWidget(self._text_edit)
        # The text is a setting also if it is not edited
        self._update()

    def _update(self) -> None:
        value = self._text_edit.toPlainText()
        self._settings[self._parameter] = value


class ComponentSettingSingleLineText(ComponentSettingsBase):
    """Text setting, in a single line"""

    def __init__(
        self,
        parent: ComponentSettingsDialog,
        parameter: str,
        parameter_dict: Parameter,
        settings: dict[str, Any],
    ) -> None:
        super().__init__(parent, parameter, parameter_dict, settings)
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        layout.addWidget(QLabel(self._parameter_dict["description"]))
        self._invalid_list = self._parameter_dict.get("invalid_list", [])
        self._line_edit = QLineEdit(self)
        default = self._parameter_dict["default"]
        while default in self._invalid_list:
            default += "x"
        self._line_edit.setText(default)
        self._line_edit.textChanged.connect(self._update)
        layout.addWidget(self._line_edit)
        self._invalid_text = QLabel()
        if len(self._invalid_list) > 0:
            layout.addWidget(self._invalid_text)
        self._update()

    def _update(self) -> None:
        value = self._line_edit.text()
        self._settings[self._parameter] = value
        if value in self._invalid_list:
            self._parent.sig_enable_ok.emit(False)
            self._invalid_text.setText("Invalid string")
        else:
            self._parent.sig_enable_ok.emit(True)
            self._invalid_text.setText("")


class ComponentSettingsSlider(ComponentSettingsBase):
    """SettingsSlider"""

    def __init__(
        self,
        parent: ComponentSettingsDialog,
        parameter: str,
        parameter_dict: Parameter,
        settings: dict[str, Any],
    ) -> None:
        super().__init__(parent, parameter, parameter_dict, settings)
        layout = QGridLayout(self)
        self.setLayout(layout)
        self._settings_slider = QSlider(Qt.Orientation.Horizontal, self)
        self._settings_slider.setSingleStep(1)
        self._settings_slider.setPageStep(1)
        self._settings_slider.setTickPosition(QSlider.TickPosition.TicksBothSides)
        self._settings_slider.valueChanged.connect(self._update)
        self._value_label = QLabel("")
        layout.addWidget(QLabel(self._parameter_dict["description"]), 0, 0, 1, 6)
        self._setup()
        layout.addWidget(self._value_label, 1, 6, 1, 1)
        layout.addWidget(self._settings_slider, 1, 0, 1, 5)
        self._init_slider()

    def _init_slider(self) -> None:
        self._settings_slider.setValue(self._parameter_dict["default"])
        self._update(self._parameter_dict["default"])

    def _setup(self) -> None:
        self._settings_slider.setMaximum(self._parameter_dict["max"])
        self._settings_slider.setMinimum(self._parameter_dict["min"])
        self._settings_slider.setValue(self._parameter_dict["default"])
        self._settings_slider.setTickInterval(
            int(max(1, (self._parameter_dict["max"] - self._parameter_dict["min"]) / 10))
        )

    def _update(self, value: int) -> None:
        self._settings[self._parameter] = value
        self._value_label.setText(f"{value}")
        self.emit_signal()


class ComponentSettingsSliderWidthPow2(ComponentSettingsSlider):
    """SettingsSlider which is dependent on bitwidth"""

    def _setup(self) -> None:
        value_max = 2 ** self._settings.get("width", 1) - 1
        self._settings_slider.setMaximum(value_max)
        self._settings_slider.setMinimum(0)
        self._settings_slider.setTickInterval(int(max(1, (value_max - 0) / 10)))

    def on_setting_change(self, parameter: str) -> None:
        if parameter == "width":
            self._setup()


class ComponentSettingsIntRangeSlider(ComponentSettingsSlider):
    """SettingsSlider (range)"""

    def _init_slider(self) -> None:
        default_index = self._parameter_dict["default_index"]
        self._settings_slider.setValue(default_index)
        self._update(default_index)

    def _setup(self) -> None:
        self._settings_slider.setMaximum(len(self._parameter_dict["range"]) - 1)
        self._settings_slider.setMinimum(0)
        self._settings_slider.setTickInterval(1)

    def _update(self, value: int) -> None:
        range_val = self._parameter_dict["range"][value]
        self._settings[self._parameter] = range_val
        self._value_label.setText(f"{range_val}")
        self.emit_signal()


class ComponentSettingsCheckBox(ComponentSettingsBase):
    """SettingsCheckbox"""

    def __init__(
        self,
        parent: ComponentSettingsDialog,
        parameter: str,
        parameter_dict: Parameter,
        settings: dict[str, Any],
    ) -> None:
        super().__init__(parent, parameter, parameter_dict, settings)
        layout = QHBoxLayout(self)
        self.setLayout(layout)
        self._settings[parameter] = parameter_dict["default"]
        self._settings_checkbox = QCheckBox(parameter_dict["description"], self)
        self._settings_checkbox.setChecked(parameter_dict["default"])
        layout.addWidget(self._settings_checkbox)
        self._settings_checkbox.stateChanged.connect(self._update)
        self._settings_checkbox.setFocus()

    def _update(self, _: int) -> None:
        self._settings[self._parameter] = self._settings_checkbox.isChecked()


class ComponentSettingsIcSelector(ComponentSettingsBase):
    """
    IC selector: a search field and the ICs that match it (see search_ics), with their
    descriptions. The arrow keys move in the list while typing, and Enter or a double
    click selects the IC and closes the dialog.
    """

    def __init__(
        self,
        parent: ComponentSettingsDialog,
        parameter: str,
        parameter_dict: Parameter,
        settings: dict[str, Any],
    ) -> None:
        super().__init__(parent, parameter, parameter_dict, settings)
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        layout.addWidget(QLabel(self._parameter_dict["description"]))
        self._ics = IntegratedCircuit.available()
        self._search = QLineEdit(self)
        self._search.setPlaceholderText("Search, like 74181, counter or shift")
        self._search.setClearButtonEnabled(True)
        self._search.installEventFilter(self)
        layout.addWidget(self._search)
        self._list = QListWidget(self)
        self._list.setMinimumWidth(380)
        layout.addWidget(self._list)
        self._search.textChanged.connect(self._filter)
        self._search.returnPressed.connect(self._accept)
        self._list.currentItemChanged.connect(self._update)
        self._list.itemDoubleClicked.connect(self._accept)
        self._filter("")
        self._search.setFocus()

    def _filter(self, query: str) -> None:
        """Show the ICs that match the search, and select the best match"""
        self._list.clear()
        for name in search_ics(query, self._ics):
            description = self._ics[name]
            item = QListWidgetItem(f"{name}  {description}" if description else name)
            item.setData(Qt.ItemDataRole.UserRole, name)
            self._list.addItem(item)
        self._list.setCurrentRow(0)
        self._update(self._list.currentItem())

    def _update(self, item: QListWidgetItem | None) -> None:
        if item is None:
            self._settings.pop(self._parameter, None)
            self._parent.sig_enable_ok.emit(False)
        else:
            self._settings[self._parameter] = item.data(Qt.ItemDataRole.UserRole)
            self._parent.sig_enable_ok.emit(True)

    def _accept(self) -> None:
        if self._list.currentItem() is not None:
            self._parent.accept()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """QT function: the arrow keys in the search field move in the list"""
        if watched is self._search and event.type() == QEvent.Type.KeyPress:
            assert isinstance(event, QKeyEvent)
            step = {Qt.Key.Key_Up: -1, Qt.Key.Key_Down: 1}.get(Qt.Key(event.key()))
            if step is not None and self._list.count() > 0:
                row = min(max(self._list.currentRow() + step, 0), self._list.count() - 1)
                self._list.setCurrentRow(row)
                return True
        return super().eventFilter(watched, event)


class ComponentSettingsNameSelector(ComponentSettingsBase):
    """Name Selector"""

    def __init__(
        self,
        parent: ComponentSettingsDialog,
        parameter: str,
        parameter_dict: Parameter,
        settings: dict[str, Any],
    ) -> None:
        super().__init__(parent, parameter, parameter_dict, settings)
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        layout.addWidget(QLabel(self._parameter_dict["description"]))
        component_dict = self._parameter_dict["component_list"]
        self._component_selector = QComboBox(parent)
        for component_name, component_desc in component_dict.items():
            self._component_selector.addItem(component_desc, userData=component_name)
        layout.addWidget(self._component_selector)
        self._component_selector.currentIndexChanged.connect(self._update)
        self._update(self._component_selector.currentIndex())

    def _update(self, value: int) -> None:
        self._settings[self._parameter] = self._component_selector.itemData(value)


class ComponentSettingsListSelector(ComponentSettingsBase):
    """List Selector"""

    def __init__(
        self,
        parent: ComponentSettingsDialog,
        parameter: str,
        parameter_dict: Parameter,
        settings: dict[str, Any],
    ) -> None:
        super().__init__(parent, parameter, parameter_dict, settings)
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        layout.addWidget(QLabel(self._parameter_dict["description"]))
        item_list = self._parameter_dict["items"]
        if len(item_list) == 0:
            raise ComponentSettingsException("No available items to choose from")

        self._item_selector = QComboBox(parent)
        for item in item_list:
            self._item_selector.addItem(item, userData=item)
        layout.addWidget(self._item_selector)
        self._item_selector.currentIndexChanged.connect(self._update)
        self._update(self._item_selector.currentIndex())

    def _update(self, value: int) -> None:
        self._settings[self._parameter] = self._item_selector.itemData(value)


class ComponentSettingsCheckBoxWidthBool(ComponentSettingsBase):
    """SettingsCheckbox for width number of bits (max32)"""

    MAX_WIDTH = 32

    def __init__(
        self,
        parent: ComponentSettingsDialog,
        parameter: str,
        parameter_dict: Parameter,
        settings: dict[str, Any],
    ) -> None:
        super().__init__(parent, parameter, parameter_dict, settings)
        layout = QGridLayout(self)
        self.setLayout(layout)
        self._bit_checkboxes: list[QCheckBox] = []
        for checkbox_id in range(self.MAX_WIDTH):
            checkbox = QCheckBox(f"bit{checkbox_id}")
            checkbox.setChecked(True)
            checkbox.stateChanged.connect(self._update)
            layout.addWidget(checkbox, checkbox_id % 8, checkbox_id // 8, 1, 1)
            self._bit_checkboxes.append(checkbox)
        disable_all = QPushButton("Disable All")
        disable_all.clicked.connect(self._disable_all)
        enable_all = QPushButton("Enable All")
        enable_all.clicked.connect(self._enable_all)
        layout.addWidget(disable_all, 8, 0, 2, 1)
        layout.addWidget(enable_all, 8, 2, 2, 1)
        self._update()

    def _set_all(self, state: bool) -> None:
        for checkbox_id in range(self.MAX_WIDTH):
            checkbox = self._bit_checkboxes[checkbox_id]
            checkbox.setChecked(state)

    def _enable_all(self) -> None:
        self._set_all(True)

    def _disable_all(self) -> None:
        self._set_all(False)

    def _update(self) -> None:
        self._settings[self._parameter] = []
        for checkbox_id in range(self.MAX_WIDTH):
            checkbox = self._bit_checkboxes[checkbox_id]
            checkbox.setEnabled(checkbox_id < self._settings["width"])
            if checkbox_id < self._settings["width"] and checkbox.isChecked():
                self._settings[self._parameter].append(checkbox_id)

    def on_setting_change(self, parameter: str) -> None:
        if parameter == "width":
            self._update()


# The input for each parameter type (see "The settings dialog" in docs/components.md)
_SETTINGS_WIDGETS: dict[str, type[ComponentSettingsBase]] = {
    "width_pow2": ComponentSettingsSliderWidthPow2,
    "width_bool": ComponentSettingsCheckBoxWidthBool,
    "int": ComponentSettingsSlider,
    "str": ComponentSettingText,
    "bool": ComponentSettingsCheckBox,
    "intrange": ComponentSettingsIntRangeSlider,
    "ic_name": ComponentSettingsIcSelector,
    "component_name": ComponentSettingsNameSelector,
    "list": ComponentSettingsListSelector,
}


class ComponentSettingsDialog(QDialog):
    """SettingsDialog"""

    sig_value_updated = Signal(str)
    sig_enable_ok = Signal(bool)

    @staticmethod
    def _is_file_path(
        parent: QWidget | None, parameters: dict[str, Parameter]
    ) -> tuple[bool, dict[str, Any]]:
        """
        If the first parameter is a file, ask for it with a file dialog. Returns if it is
        a file, and the settings with the file (empty if the dialog was cancelled).
        """
        first_key = next(iter(parameters))
        settings = {}
        is_file_path = parameters[first_key]["type"] == "path"
        if is_file_path:
            description = parameters[first_key]["description"]
            fileinfo = parameters[first_key]["fileinfo"]
            path = QFileDialog.getOpenFileName(
                parent, description, "", f"{fileinfo};;All Files (*.*)"
            )
            if len(path[0]) > 0:
                settings[first_key] = path[0]
        return is_file_path, settings

    @classmethod
    def start(
        cls,
        parent: QWidget | None,
        app_model: AppModel,
        name: str,
        parameters: dict[str, Parameter],
    ) -> tuple[bool, dict[str, Any]]:
        """Start a settings dialog and return the settings"""
        if len(parameters) == 0:
            # No parameters, just place component without settings
            return True, {}

        is_file_path, settings = cls._is_file_path(parent, parameters)
        if is_file_path:
            if len(settings) == 0:
                return False, {}
            # The other parameters in a dialog after the file, if there are any
            parameters = {key: value for key, value in parameters.items() if key not in settings}
            if len(parameters) == 0:
                return True, settings

        try:
            dialog = ComponentSettingsDialog(parent, app_model, name, parameters)
            result = dialog.exec()
            if result == QDialog.DialogCode.Rejected:
                return False, {}
            return True, {**settings, **dialog.get_settings()}
        except ComponentSettingsException as exc:
            app_model.sig_error.emit(str(exc))
            return False, {}

    def _setup_dialog(self, parameters: dict[str, Parameter]) -> None:
        for parameter, parameter_dict in parameters.items():
            parameter_type = parameter_dict["type"]
            if parameter_type == "str" and parameter_dict.get("single_line", False):
                widget_class: type[ComponentSettingsBase] = ComponentSettingSingleLineText
            elif parameter_type in _SETTINGS_WIDGETS:
                widget_class = _SETTINGS_WIDGETS[parameter_type]
            else:
                self._app_model.sig_error.emit(f"Unknown settings type '{parameter_type}'")
                continue
            self._layout.addWidget(widget_class(self, parameter, parameter_dict, self._settings))

    def __init__(
        self,
        parent: QWidget | None,
        app_model: AppModel,
        name: str,
        parameters: dict[str, Parameter],
    ) -> None:
        super().__init__(parent)
        self._app_model = app_model
        self._layout = QVBoxLayout(self)
        self.setLayout(self._layout)
        self.setWindowTitle(f"Setup {name}")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._settings: dict[str, Any] = {}
        self._setup_dialog(parameters)
        self.buttonBox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self._layout.addWidget(self.buttonBox)
        self.sig_enable_ok.connect(self._enable_ok)

    def _enable_ok(self, enable: bool) -> None:
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(enable)

    def get_settings(self) -> dict[str, Any]:
        """Get settings from setting dialog"""
        return self._settings
