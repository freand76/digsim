# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""The GUI settings dialog"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QComboBox, QDialog, QDialogButtonBox, QGridLayout, QLabel


class GuiSettingsDialog(QDialog):
    """GUI Settings Dialog"""

    def __init__(self, parent, app_model):
        super().__init__(parent)
        self._app_model = app_model
        self.setLayout(QGridLayout(self))
        self.setWindowTitle("Application Settings")
        self.setFocusPolicy(Qt.StrongFocus)

        # GUI Update Frequency
        self._update_frequency = QComboBox(self)
        for frequency in [1, 10, 20, 50, 100]:
            self._update_frequency.addItem(f"{frequency} Hz", userData=frequency)

        self._slow_to_real_time = QCheckBox("", self)
        self._show_wire_value = QCheckBox("", self)

        # OK / Cancel
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        # Layout
        row = 0
        self.layout().addWidget(QLabel("GUI Update Frequency", self), row, 0, 1, 1)
        self.layout().addWidget(self._update_frequency, row, 1, 1, 1)
        row += 1
        self.layout().addWidget(QLabel("Slow down sim to 'Real Time'", self), row, 0, 1, 1)
        self.layout().addWidget(self._slow_to_real_time, row, 1, 1, 1)
        row += 1
        self.layout().addWidget(QLabel("Show Wire Value", self), row, 0, 1, 1)
        self.layout().addWidget(self._show_wire_value, row, 1, 1, 1)
        row += 1
        self.layout().addWidget(self.buttonBox, row, 0, 1, 2, alignment=Qt.AlignCenter)

        self._settings = self._app_model.settings.get_all()
        self._slow_to_real_time.setChecked(self._settings["real_time"])
        self._show_wire_value.setChecked(self._settings["color_wires"])

        index = self._update_frequency.findData(self._settings["update_frequency"])
        self._update_frequency.setCurrentIndex(index)

    @classmethod
    def default_settings(cls):
        """Default settings"""
        return {
            "real_time": True,
            "color_wires": True,
            "update_frequency": 20,
        }

    def start(self):
        """Start Dialog"""
        result = self.exec_()
        if result == QDialog.DialogCode.Accepted:
            self._settings["real_time"] = self._slow_to_real_time.isChecked()
            self._settings["color_wires"] = self._show_wire_value.isChecked()
            self._settings["update_frequency"] = self._update_frequency.itemData(
                self._update_frequency.currentIndex()
            )
            self._app_model.settings.update(self._settings)
