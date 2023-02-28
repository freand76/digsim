# Copyright (c) Fredrik Andersson, 2023
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


def are_you_sure_delete_component(parent, component_name=None):
    """Are you sure messagebox"""
    if component_name is not None:
        message_text = f"Are you sure want to delete the '{component_name}' component?"
    else:
        message_text = "Are you sure want to delete the selected component(s)?"

    return warning_messagebox(
        parent,
        "Delete component?",
        message_text,
    )
