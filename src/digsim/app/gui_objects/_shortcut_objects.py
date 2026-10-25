# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""The keyboard shortcut of an input component, like a push button"""

from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QWidget

from digsim.app.settings import ShortcutDialog
from digsim.circuit.components.atoms import Component


if TYPE_CHECKING:
    from digsim.app.model import AppModel


class ShortcutMenu:
    """The Shortcut entry of the context menu of an input component"""

    @classmethod
    def add_context_menu_action(
        cls, menu: QMenu, parent: QWidget | None, app_model: AppModel, component: Component
    ) -> None:
        """Add context menu action"""
        shortcutAction = QAction("Shortcut", menu)
        menu.addAction(shortcutAction)
        shortcutAction.triggered.connect(partial(cls._shortcut, parent, app_model, component))

    @classmethod
    def _shortcut(cls, parent: QWidget | None, app_model: AppModel, component: Component) -> None:
        shortcutDialog = ShortcutDialog(parent, app_model)
        key = shortcutDialog.start()
        if key is not None:
            app_model.shortcuts.set_component(key, component)
