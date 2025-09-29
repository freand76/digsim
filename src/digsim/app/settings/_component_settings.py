# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""The component settings dialog(s)"""

import pathlib

from PySide6.QtCore import Qt, Signal
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
    QPushButton,
    QSlider,
    QTextEdit,
    QVBoxLayout,
)

from digsim.circuit.components import IntegratedCircuit


class ComponentSettingsException(Exception):
    """ComponentSettingsException"""


class ComponentSettingsBase(QFrame):
    """SettingsBase"""

    def __init__(self, parent, parameter, parameter_dict, settings):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Panel)
        self._parent = parent
        self._parameter = parameter
        self._parameter_dict = parameter_dict
        self._settings = settings
        self._parent.sig_value_updated.connect(self._on_setting_change)

    def emit_signal(self):
        """Signal other settings components that a value has changed"""
        self._parent.sig_value_updated.emit(self._parameter)

    def _on_setting_change(self, parameter):
        if parameter != self._parameter:
            self.on_setting_change(parameter)

    def on_setting_change(self, parameter):
        """Called when other setting is changed"""


class ComponentSettingText(ComponentSettingsBase):
    """Text setting"""

    def __init__(self, parent, parameter, parameter_dict, settings):
        super().__init__(parent, parameter, parameter_dict, settings)
        self.setLayout(QVBoxLayout(self))
        self.layout().addWidget(QLabel(self._parameter_dict["description"]))
        self._text_edit = QTextEdit(self)
        self._text_edit.setText(self._parameter_dict["default"])
        self._text_edit.textChanged.connect(self._update)
        self.layout().addWidget(self._text_edit)

    def _update(self):
        value = self._text_edit.toPlainText()
        self._settings[self._parameter] = value


class ComponentSettingSingleLineText(ComponentSettingsBase):
    """Text setting"""

    def __init__(self, parent, parameter, parameter_dict, settings):
        super().__init__(parent, parameter, parameter_dict, settings)
        self._parent = parent
        self.setLayout(QVBoxLayout(self))
        self.layout().addWidget(QLabel(self._parameter_dict["description"]))
        self._invalid_list = self._parameter_dict.get("invalid_list", [])
        self._line_edit = QLineEdit(self)
        default = self._parameter_dict["default"]
        while default in self._invalid_list:
            default += "x"
        self._line_edit.setText(default)
        self._settings[self._parameter] = self._parameter_dict["default"]
        self._line_edit.textChanged.connect(self._update)
        self.layout().addWidget(self._line_edit)
        self._invalid_text = QLabel()
        if len(self._invalid_list) > 0:
            self.layout().addWidget(self._invalid_text)
        self._update()

    def _update(self):
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

    def __init__(self, parent, parameter, parameter_dict, settings):
        super().__init__(parent, parameter, parameter_dict, settings)
        self.setLayout(QGridLayout(self))
        self._settings_slider = QSlider(Qt.Horizontal, self)
        self._settings_slider.setSingleStep(1)
        self._settings_slider.setPageStep(1)
        self._settings_slider.setTickPosition(QSlider.TicksBothSides)
        self._settings_slider.valueChanged.connect(self._update)
        self._value_label = QLabel("")
        self.layout().addWidget(QLabel(self._parameter_dict["description"]), 0, 0, 1, 6)
        self._setup()
        self.layout().addWidget(self._value_label, 1, 6, 1, 1)
        self.layout().addWidget(self._settings_slider, 1, 0, 1, 5)
        self._init_slider()

    def _init_slider(self):
        self._settings_slider.setValue(self._parameter_dict["default"])
        self._update(self._parameter_dict["default"])

    def _setup(self):
        self._settings_slider.setMaximum(self._parameter_dict["max"])
        self._settings_slider.setMinimum(self._parameter_dict["min"])
        self._settings_slider.setValue(self._parameter_dict["default"])
        self._settings_slider.setTickInterval(
            max(1, (self._parameter_dict["max"] - self._parameter_dict["min"]) / 10)
        )

    def _update(self, value):
        self._settings[self._parameter] = value
        self._value_label.setText(f"{value}")
        self.emit_signal()


class ComponentSettingsSliderWidthPow2(ComponentSettingsSlider):
    """SettingsSlider which is dependent on bitwidth"""

    def _setup(self):
        value_max = 2 ** self._settings.get("width", 1) - 1
        self._settings_slider.setMaximum(value_max)
        self._settings_slider.setMinimum(0)
        self._settings_slider.setTickInterval(max(1, (value_max - 0) / 10))

    def _update(self, value):
        self._settings[self._parameter] = value
        self._value_label.setText(f"{value}")
        self.emit_signal()

    def on_setting_change(self, parameter):
        if parameter == "width":
            self._setup()


class ComponentSettingsIntRangeSlider(ComponentSettingsSlider):
    """SettingsSlider (range)"""

    def _init_slider(self):
        default_index = self._parameter_dict["default_index"]
        self._settings_slider.setValue(default_index)
        self._update(default_index)

    def _setup(self):
        self._settings_slider.setMaximum(len(self._parameter_dict["range"]) - 1)
        self._settings_slider.setMinimum(0)
        self._settings_slider.setTickInterval(1)

    def _update(self, value):
        range_val = self._parameter_dict["range"][value]
        self._settings[self._parameter] = range_val
        self._value_label.setText(f"{range_val}")
        self.emit_signal()


class ComponentSettingsCheckBox(ComponentSettingsBase):
    """SettingsCheckbox"""

    def __init__(self, parent, parameter, parameter_dict, settings):
        super().__init__(parent, parameter, parameter_dict, settings)
        self.setLayout(QHBoxLayout(self))
        self.setFrameStyle(QFrame.Panel)
        self._settings[parameter] = parameter_dict["default"]
        self._settings_checkbox = QCheckBox(parameter_dict["description"], self)
        self._settings_checkbox.setChecked(parameter_dict["default"])
        self.layout().addWidget(self._settings_checkbox)
        self._settings_checkbox.stateChanged.connect(self._update)
        self._settings_checkbox.setFocus()

    def _update(self, _):
        self._settings[self._parameter] = self._settings_checkbox.isChecked()


class ComponentSettingsIcSelector(ComponentSettingsBase):
    """IC Selector"""

    def __init__(self, parent, parameter, parameter_dict, settings):
        super().__init__(parent, parameter, parameter_dict, settings)
        self.setLayout(QVBoxLayout(self))
        self.layout().addWidget(QLabel(self._parameter_dict["description"]))
        ic_folder = IntegratedCircuit.folder()
        ic_files = pathlib.Path(ic_folder).glob("*.json")
        self._ic_selector = QComboBox(parent)
        for ic_file in ic_files:
            self._ic_selector.addItem(ic_file.stem, userData=ic_file.stem)
        self.layout().addWidget(self._ic_selector)
        self._ic_selector.currentIndexChanged.connect(self._update)
        self._update(self._ic_selector.currentIndex())

    def _update(self, value):
        self._settings[self._parameter] = self._ic_selector.itemData(value)


class ComponentSettingsNameSelector(ComponentSettingsBase):
    """Name Selector"""

    def __init__(self, parent, parameter, parameter_dict, settings):
        super().__init__(parent, parameter, parameter_dict, settings)
        self.setLayout(QVBoxLayout(self))
        self.layout().addWidget(QLabel(self._parameter_dict["description"]))
        component_dict = self._parameter_dict["component_list"]
        self._component_selector = QComboBox(parent)
        for component_name, component_desc in component_dict.items():
            self._component_selector.addItem(component_desc, userData=component_name)
        self.layout().addWidget(self._component_selector)
        self._component_selector.currentIndexChanged.connect(self._update)
        self._update(self._component_selector.currentIndex())

    def _update(self, value):
        self._settings[self._parameter] = self._component_selector.itemData(value)


class ComponentSettingsListSelector(ComponentSettingsBase):
    """List Selector"""

    def __init__(self, parent, parameter, parameter_dict, settings):
        super().__init__(parent, parameter, parameter_dict, settings)
        self.setLayout(QVBoxLayout(self))
        self.layout().addWidget(QLabel(self._parameter_dict["description"]))
        item_list = self._parameter_dict["items"]
        if len(item_list) == 0:
            raise ComponentSettingsException("No available items to choose from")

        self._item_selector = QComboBox(parent)
        for item in item_list:
            self._item_selector.addItem(item, userData=item)
        self.layout().addWidget(self._item_selector)
        self._item_selector.currentIndexChanged.connect(self._update)
        self._update(self._item_selector.currentIndex())

    def _update(self, value):
        self._settings[self._parameter] = self._item_selector.itemData(value)


class ComponentSettingsCheckBoxWidthBool(ComponentSettingsBase):
    """SettingsCheckbox for width number of bits (max32)"""

    MAX_WIDTH = 32

    def __init__(self, parent, parameter, parameter_dict, settings):
        super().__init__(parent, parameter, parameter_dict, settings)
        self.setLayout(QGridLayout(self))
        self._bit_checkboxes = []
        for checkbox_id in range(self.MAX_WIDTH):
            checkbox = QCheckBox(f"bit{checkbox_id}")
            checkbox.setChecked(True)
            checkbox.stateChanged.connect(self._update)
            self.layout().addWidget(checkbox, checkbox_id % 8, checkbox_id // 8, 1, 1)
            self._bit_checkboxes.append(checkbox)
        disable_all = QPushButton("Disable All")
        disable_all.clicked.connect(self._disable_all)
        enable_all = QPushButton("Enable All")
        enable_all.clicked.connect(self._enable_all)
        self.layout().addWidget(disable_all, 8, 0, 2, 1)
        self.layout().addWidget(enable_all, 8, 2, 2, 1)
        self._update()

    def _set_all(self, state):
        for checkbox_id in range(self.MAX_WIDTH):
            checkbox = self._bit_checkboxes[checkbox_id]
            checkbox.setChecked(state)

    def _enable_all(self):
        self._set_all(True)

    def _disable_all(self):
        self._set_all(False)

    def _update(self):
        self._settings[self._parameter] = []
        for checkbox_id in range(32):
            checkbox = self._bit_checkboxes[checkbox_id]
            checkbox.setEnabled(checkbox_id < self._settings["width"])
            if checkbox_id < self._settings["width"] and checkbox.isChecked():
                self._settings[self._parameter].append(checkbox_id)

    def on_setting_change(self, parameter):
        if parameter == "width":
            self._update()


class ComponentSettingsDialog(QDialog):
    """SettingsDialog"""

    sig_value_updated = Signal(str)
    sig_enable_ok = Signal(bool)

    @staticmethod
    def _is_file_path(parent, parameters):
        parameters_list = list(parameters.keys())
        first_key = parameters_list[0]
        settings = {}
        is_file_path = len(parameters_list) == 1 and parameters[first_key]["type"] == "path"
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
    def start(cls, parent, app_model, name, parameters):
        """Start a settings dialog and return the settings"""
        if len(parameters) == 0:
            # No parameters, just place component without settings
            return True, {}

        is_file_path, settings = cls._is_file_path(parent, parameters)
        if is_file_path:
            return len(settings) > 0, settings

        try:
            dialog = ComponentSettingsDialog(parent, app_model, name, parameters)
            result = dialog.exec_()
            if result == QDialog.DialogCode.Rejected:
                return False, {}
            return True, dialog.get_settings()
        except ComponentSettingsException as exc:
            app_model.sig_error.emit(str(exc))
            return False, {}

    def _setup_dialog(self, parameters):
        for parameter, parameter_dict in parameters.items():
            if parameter_dict["type"] == "width_pow2":
                widget = ComponentSettingsSliderWidthPow2(
                    self, parameter, parameter_dict, self._settings
                )
            elif parameter_dict["type"] == "width_bool":
                widget = ComponentSettingsCheckBoxWidthBool(
                    self, parameter, parameter_dict, self._settings
                )
            elif parameter_dict["type"] == "int":
                widget = ComponentSettingsSlider(self, parameter, parameter_dict, self._settings)
            elif parameter_dict["type"] == "str":
                single_line = parameter_dict.get("single_line", False)
                if single_line:
                    widget = ComponentSettingSingleLineText(
                        self, parameter, parameter_dict, self._settings
                    )
                else:
                    widget = ComponentSettingText(self, parameter, parameter_dict, self._settings)
            elif parameter_dict["type"] == "bool":
                widget = ComponentSettingsCheckBox(self, parameter, parameter_dict, self._settings)
            elif parameter_dict["type"] == "intrange":
                widget = ComponentSettingsIntRangeSlider(
                    self, parameter, parameter_dict, self._settings
                )
            elif parameter_dict["type"] == "ic_name":
                widget = ComponentSettingsIcSelector(
                    self, parameter, parameter_dict, self._settings
                )
            elif parameter_dict["type"] == "component_name":
                widget = ComponentSettingsNameSelector(
                    self, parameter, parameter_dict, self._settings
                )
            elif parameter_dict["type"] == "list":
                widget = ComponentSettingsListSelector(
                    self, parameter, parameter_dict, self._settings
                )
            else:
                self._app_model.sig_error.emit(f"Unknown settings type '{parameter_dict['type']}'")
                continue

            self.layout().addWidget(widget)

    def __init__(self, parent, app_model, name, parameters):
        super().__init__(parent)
        self._app_model = app_model
        self.setLayout(QVBoxLayout(self))
        self.setWindowTitle(f"Setup {name}")
        self.setFocusPolicy(Qt.StrongFocus)
        self._settings = {}
        self._setup_dialog(parameters)
        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.layout().addWidget(self.buttonBox)
        self.sig_enable_ok.connect(self._enable_ok)

    def _enable_ok(self, enable):
        self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(enable)

    def get_settings(self):
        """Get settings from setting dialog"""
        return self._settings
