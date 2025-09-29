# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Module with utility functions shared in the GUI"""

from PySide6.QtWidgets import QMessageBox


def warning_messagebox(parent, dialog_text, message_text):
    """Are you sure messagebox"""
    result = QMessageBox.question(
        parent,
        dialog_text,
        message_text,
        QMessageBox.Yes | QMessageBox.No,
    )
    return result == QMessageBox.Yes


def are_you_sure_destroy_circuit(parent, dialog_text):
    """Are you sure messagebox"""
    return warning_messagebox(
        parent,
        dialog_text,
        "Are you sure want to destroy the current circuit?",
    )
