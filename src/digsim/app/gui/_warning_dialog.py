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
)


class WarningDialog(QDialog):
    """WarningDialog"""

    def __init__(self, parent, title, warning_message):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setLayout(QVBoxLayout(self))
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setStyleSheet("QLabel{font-size: 18pt;}")
        frame = QFrame(parent)
        frame.setLayout(QHBoxLayout(frame))
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        frame.setFrameShadow(QFrame.Shadow.Sunken)
        label = QLabel()
        label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        label.setText(warning_message)
        icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxWarning)
        button = QLabel()
        button.setPixmap(icon.pixmap(QSize(32, 32)))
        frame.layout().addWidget(button)
        frame.layout().setStretchFactor(label, 0)
        frame.layout().addWidget(label)
        frame.layout().setStretchFactor(label, 1)
        buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttonBox.accepted.connect(self.accept)
        self.layout().addWidget(frame)
        self.layout().setStretchFactor(frame, 1)
        self.layout().addWidget(buttonBox)
        self.layout().setStretchFactor(buttonBox, 0)
