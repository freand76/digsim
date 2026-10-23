# Copyright (c) Fredrik Andersson, 2023-2024
# All rights reserved

"""A warning dialog"""

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from digsim.app.settings._dialog_flags import DIALOG_FLAGS


class WarningDialog(QDialog):
    """WarningDialog"""

    def __init__(self, parent: QWidget | None, title: str, warning_message: str) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        # Only a close button: a dialog is not minimized or maximized
        self.setWindowFlags(DIALOG_FLAGS)
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setStyleSheet("QLabel{font-size: 18pt;}")
        frame = QFrame(parent)
        frame_layout = QHBoxLayout(frame)
        frame.setLayout(frame_layout)
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        frame.setFrameShadow(QFrame.Shadow.Sunken)
        label = QLabel()
        label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        label.setText(warning_message)
        icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxWarning)
        icon_label = QLabel()
        icon_label.setPixmap(icon.pixmap(QSize(32, 32)))
        frame_layout.addWidget(icon_label)
        frame_layout.addWidget(label)
        frame_layout.setStretchFactor(label, 1)
        buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttonBox.accepted.connect(self.accept)
        layout.addWidget(frame)
        layout.setStretchFactor(frame, 1)
        layout.addWidget(buttonBox)
        layout.setStretchFactor(buttonBox, 0)
