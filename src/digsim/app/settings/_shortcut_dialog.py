# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

"""The shurtcut dialog"""

# pylint: disable=too-few-public-methods

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QLabel, QVBoxLayout


class ShortcutDialog(QDialog):
    """Shortcut Dialog"""

    def __init__(self, parent, app_model):
        super().__init__(parent)
        self._app_model = app_model
        self.setLayout(QVBoxLayout(self))
        self.setWindowTitle("Add shortcut")
        self.setFocusPolicy(Qt.StrongFocus)

        self.layout().addWidget(QLabel("Select shortcut key for component"))
        self._key_selector = QComboBox(parent)
        for key in "1234567890":
            shortcut_key = str(key)
            shortcut_string = shortcut_key
            shortcut_component = app_model.shortcuts.get_component(shortcut_key)
            if shortcut_component is not None:
                shortcut_string += f" - {shortcut_component.name()}"
            self._key_selector.addItem(shortcut_string, userData=shortcut_key)
        self.layout().addWidget(self._key_selector)
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.layout().addWidget(self.buttonBox)

    def start(self):
        """Start Dialog"""
        result = self.exec_()
        if result == QDialog.DialogCode.Rejected:
            return None
        return self._key_selector.currentData()
