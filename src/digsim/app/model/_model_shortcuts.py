# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Handle shortcuts in the model"""

from __future__ import annotations

import typing
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt

from digsim.circuit.components.atoms import Component, DigsimException


if TYPE_CHECKING:
    from ._model import AppModel


class ModelShortcuts:
    """class to handle key shortcuts in the model"""

    QT_KEY_TO_KEY: typing.ClassVar[dict[int, str]] = {
        Qt.Key.Key_0: "0",
        Qt.Key.Key_1: "1",
        Qt.Key.Key_2: "2",
        Qt.Key.Key_3: "3",
        Qt.Key.Key_4: "4",
        Qt.Key.Key_5: "5",
        Qt.Key.Key_6: "6",
        Qt.Key.Key_7: "7",
        Qt.Key.Key_8: "8",
        Qt.Key.Key_9: "9",
    }

    def __init__(self, app_model: AppModel) -> None:
        self._app_model = app_model
        # Component names: undo and redo replace the components with new ones
        self._shortcut_component: dict[str, str] = {}

    def clear(self) -> None:
        """Clear shortcuts"""
        self._shortcut_component = {}

    def set_component(self, key: str, component: Component) -> None:
        """Set shortcut"""
        self._shortcut_component[key] = component.name()

    def get_component(self, key: str) -> Component | None:
        """Get shortcut, None if its component is not in the circuit (anymore)"""
        component_name = self._shortcut_component.get(key)
        if component_name is None:
            return None
        try:
            return self._app_model.objects.circuit.get_component(component_name)
        except DigsimException:
            return None

    def press(self, qtkey: int) -> None:
        """Handle shortcut keypress"""
        key = self.QT_KEY_TO_KEY.get(qtkey)
        if key is None:
            return
        component = self.get_component(key)
        if component is not None:
            self._app_model.model_add_event(component.onpress)

    def release(self, qtkey: int) -> None:
        """Handle shortcut keyrelease"""
        key = self.QT_KEY_TO_KEY.get(qtkey)
        if key is None:
            return
        component = self.get_component(key)
        if component is not None:
            self._app_model.model_add_event(component.onrelease)

    def to_dict(self) -> dict[str, str]:
        """Generate dict from shortcuts"""
        shortcuts_dict = {}
        for key in self._shortcut_component:
            component = self.get_component(key)
            if component is not None:
                shortcuts_dict[key] = component.name()
        return shortcuts_dict

    def from_dict(self, shortcuts_dict: dict[str, str] | None) -> None:
        """Generate shortcuts from dict"""
        self.clear()
        if shortcuts_dict is not None:
            self._shortcut_component = dict(shortcuts_dict)
