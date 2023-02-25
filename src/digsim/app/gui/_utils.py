# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

"""Module with utility functions shared in the GUI"""

from PySide6.QtWidgets import QMessageBox


def are_you_sure_messagebox(parent, dialog_text):
    """Are you sure messagebox"""
    result = QMessageBox.question(
        parent,
        dialog_text,
        "Are you sure want to destroy the current circuit?",
        QMessageBox.Yes | QMessageBox.No,
    )
    return result == QMessageBox.Yes
