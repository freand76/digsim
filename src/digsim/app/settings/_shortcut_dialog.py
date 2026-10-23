# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""The shurtcut dialog"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLayout,
    QVBoxLayout,
    QWidget,
)

from ._dialog_flags import DIALOG_FLAGS


if TYPE_CHECKING:
    from digsim.app.model import AppModel


class ShortcutDialog(QDialog):
    """Shortcut Dialog"""

    def __init__(self, parent: QWidget | None, app_model: AppModel) -> None:
        super().__init__(parent)
        self._app_model = app_model
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        self.setWindowTitle("Add shortcut")
        # Only a close button: a dialog is not minimized or maximized
        self.setWindowFlags(DIALOG_FLAGS)
        layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        layout.addWidget(QLabel("Select shortcut key for component"))
        self._key_selector = QComboBox(parent)
        for key in "1234567890":
            shortcut_string = key
            shortcut_component = app_model.shortcuts.get_component(key)
            if shortcut_component is not None:
                shortcut_string += f" - {shortcut_component.name()}"
            self._key_selector.addItem(shortcut_string, userData=key)
        layout.addWidget(self._key_selector)
        self.buttonBox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        layout.addWidget(self.buttonBox)

    def start(self) -> str | None:
        """Start Dialog"""
        result = self.exec()
        if result == QDialog.DialogCode.Rejected:
            return None
        return self._key_selector.currentData()
