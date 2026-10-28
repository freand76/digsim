# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""
The settings of the application, for all circuits, like the recent files (a circuit's own
settings are in its file)
"""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QSettings


# Simulations go on in the tabs that aren't shown (off: a tab stops when another is shown)
HIDDEN_TABS_KEY = "simulation/hidden_tabs"


def app_settings() -> QSettings:
    """
    The settings of the application. DIGSIM_SETTINGS_DIR sets another folder for them,
    like scripts and tests do.
    """
    folder = os.environ.get("DIGSIM_SETTINGS_DIR")
    if folder:
        return QSettings(str(Path(folder) / "digsim.ini"), QSettings.Format.IniFormat)
    return QSettings(QSettings.Format.IniFormat, QSettings.Scope.UserScope, "digsim", "digsim")


def simulate_hidden_tabs() -> bool:
    """Do simulations go on in the tabs that aren't shown"""
    return bool(app_settings().value(HIDDEN_TABS_KEY, False, type=bool))
