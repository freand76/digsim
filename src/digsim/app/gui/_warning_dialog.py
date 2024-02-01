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
        self.setFocusPolicy(Qt.StrongFocus)
        self.setStyleSheet("QLabel{font-size: 18pt;}")
        frame = QFrame(parent)
        frame.setLayout(QHBoxLayout(frame))
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setFrameShadow(QFrame.Sunken)
        label = QLabel()
        label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        label.setText(warning_message)
        icon = self.style().standardIcon(QStyle.SP_MessageBoxWarning)
        button = QLabel()
        button.setPixmap(icon.pixmap(QSize(32, 32)))
        frame.layout().addWidget(button)
        frame.layout().setStretchFactor(label, 0)
        frame.layout().addWidget(label)
        frame.layout().setStretchFactor(label, 1)
        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok)
        buttonBox.accepted.connect(self.accept)
        self.layout().addWidget(frame)
        self.layout().setStretchFactor(frame, 1)
        self.layout().addWidget(buttonBox)
        self.layout().setStretchFactor(buttonBox, 0)
