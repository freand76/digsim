# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""The theme of the application: light or dark, or as the system has it"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QGuiApplication, QPalette
from PySide6.QtWidgets import QApplication

from digsim.app.gui_objects import _theme as theme


# View > Theme: as the system has it, or always light or dark
THEMES = {"system": "&System", "light": "&Light", "dark": "&Dark"}

# The palette the application started with, the system's
_system_palette: QPalette | None = None


def system_is_dark() -> bool:
    """Does the system have a dark color scheme"""
    return QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark


def _dark_palette() -> QPalette:
    palette = QPalette()
    colors = {
        QPalette.ColorRole.Window: "#24292e",
        QPalette.ColorRole.WindowText: "#d3dae1",
        QPalette.ColorRole.Base: "#1b1f24",
        QPalette.ColorRole.AlternateBase: "#2a3037",
        QPalette.ColorRole.ToolTipBase: "#2a3037",
        QPalette.ColorRole.ToolTipText: "#d3dae1",
        QPalette.ColorRole.PlaceholderText: "#7a858f",
        QPalette.ColorRole.Text: "#d3dae1",
        QPalette.ColorRole.Button: "#2f353c",
        QPalette.ColorRole.ButtonText: "#d3dae1",
        QPalette.ColorRole.BrightText: "#ff6166",
        QPalette.ColorRole.Highlight: "#4d94ff",
        QPalette.ColorRole.HighlightedText: "#ffffff",
        QPalette.ColorRole.Link: "#6aa8ff",
        QPalette.ColorRole.Light: "#3a4149",
        QPalette.ColorRole.Midlight: "#343b42",
        QPalette.ColorRole.Mid: "#2a3037",
        QPalette.ColorRole.Dark: "#15191d",
        QPalette.ColorRole.Shadow: "#0d0f12",
    }
    for role, color in colors.items():
        palette.setColor(role, QColor(color))
    for role in (
        QPalette.ColorRole.WindowText,
        QPalette.ColorRole.Text,
        QPalette.ColorRole.ButtonText,
    ):
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor("#69737d"))
    return palette


def apply_theme(choice: str) -> bool:
    """
    Use a theme, "system", "light" or "dark": the palette of the widgets and the colors
    of the circuit (see _theme.set_dark). Returns True if it is dark. The widgets that
    made something from the colors of the circuit before have to make it again.
    """
    global _system_palette
    app = QApplication.instance()
    assert isinstance(app, QApplication)
    if _system_palette is None:
        _system_palette = app.palette()
    hints = QGuiApplication.styleHints()
    # The system's scheme, without the one of the theme chosen before
    hints.setColorScheme(Qt.ColorScheme.Unknown)
    system_dark = system_is_dark()
    dark = choice == "dark" or (choice == "system" and system_dark)
    scheme = {"light": Qt.ColorScheme.Light, "dark": Qt.ColorScheme.Dark}
    hints.setColorScheme(scheme.get(choice, Qt.ColorScheme.Unknown))
    if dark:
        app.setPalette(_dark_palette())
    elif system_dark:
        # Light, on a system that is dark
        app.setPalette(app.style().standardPalette())
    else:
        app.setPalette(_system_palette)
    theme.set_dark(dark)
    return dark
