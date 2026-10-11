# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Module with utility functions shared in the GUI"""

from PySide6.QtWidgets import QMessageBox, QWidget


def warning_messagebox(parent: QWidget | None, dialog_text: str, message_text: str) -> bool:
    """Are you sure messagebox"""
    result = QMessageBox.question(
        parent,
        dialog_text,
        message_text,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    )
    return result == QMessageBox.StandardButton.Yes


def are_you_sure_destroy_circuit(parent: QWidget | None, dialog_text: str) -> bool:
    """Are you sure messagebox"""
    return warning_messagebox(
        parent,
        dialog_text,
        "Are you sure want to destroy the current circuit?",
    )
