# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Handle shortcuts in the model"""

from PySide6.QtCore import Qt


class ModelShortcuts:
    """class to handle key shortcuts in the model"""

    QT_KEY_TO_KEY = {
        Qt.Key_0: "0",
        Qt.Key_1: "1",
        Qt.Key_2: "2",
        Qt.Key_3: "3",
        Qt.Key_4: "4",
        Qt.Key_5: "5",
        Qt.Key_6: "6",
        Qt.Key_7: "7",
        Qt.Key_8: "8",
        Qt.Key_9: "9",
    }

    def __init__(self, app_model):
        self._app_model = app_model
        self._shortcut_component = {}

    def clear(self):
        """Clear shortcuts"""
        self._shortcut_component = {}

    def set_component(self, key, component):
        """Set shortcut"""
        self._shortcut_component[key] = component

    def get_component(self, key):
        """Get shortcut"""
        return self._shortcut_component.get(key)

    def press(self, qtkey):
        """Handle shortcut keypress"""
        key = self.QT_KEY_TO_KEY.get(qtkey)
        if key is None:
            return
        component = self.get_component(key)
        if component is not None:
            self._app_model.model_add_event(component.onpress)

    def release(self, qtkey):
        """Handle shortcut keyrelease"""
        key = self.QT_KEY_TO_KEY.get(qtkey)
        if key is None:
            return
        component = self.get_component(key)
        if component is not None:
            self._app_model.model_add_event(component.onrelease)

    def to_dict(self):
        """Generate dict from shortcuts"""
        shortcuts_dict = {}
        for key, component in self._shortcut_component.items():
            shortcuts_dict[key] = component.name()
        return shortcuts_dict

    def from_dict(self, shortcuts_dict):
        """Generate shortcuts from dict"""
        self.clear()
        if shortcuts_dict is not None:
            for key, component_name in shortcuts_dict.items():
                component = self._app_model.objects.circuit.get_component(component_name)
                self.set_component(key, component)
