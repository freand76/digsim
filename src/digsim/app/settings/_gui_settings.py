# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

"""The GUI settings dialog"""

# pylint: disable=too-few-public-methods

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFontDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
)


class GuiSettingsDialog(QDialog):
    """GUI Settings Dialog"""

    def __init__(self, parent, app_model):
        super().__init__(parent)
        self._app_model = app_model
        self.setLayout(QVBoxLayout(self))
        self.setWindowTitle("Application Settings")
        self.setFocusPolicy(Qt.StrongFocus)
        self.setStyleSheet("QLabel{font-size: 18pt;}")

        self._font_select_button = QPushButton("Select Note Font", self)
        self._font_select_button.clicked.connect(self._font_selector)
        self.layout().addWidget(self._font_select_button)

        self._font_name_label = QLabel("<font name>", self)
        self.layout().addWidget(self._font_name_label)

        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.layout().addWidget(self.buttonBox)
        self._settings = {}

    def _font_selector(self):
        font_dialog = QFontDialog(self)
        font_dialog.setOptions(QFontDialog.ScalableFonts | QFontDialog.DontUseNativeDialog)
        result = font_dialog.exec_()
        if result == QDialog.DialogCode.Accepted:
            font = font_dialog.currentFont()
            self._settings["note_font"] = font.toString()
            self._font_name_label.setText(font.toString().split(",")[0])

    def start(self):
        """Start Dialog"""
        result = self.exec_()
        if result == QDialog.DialogCode.Accepted:
            self._app_model.settings.update(self._settings)
