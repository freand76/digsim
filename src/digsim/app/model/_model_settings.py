# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Handle settings in the model"""

from digsim.app.settings import GuiSettingsDialog


class ModelSettings:
    """Class to handle settings in the model"""

    def __init__(self, app_model):
        self._app_model = app_model
        self._settings = GuiSettingsDialog.default_settings()

    def update(self, settings):
        """Update model settings"""
        self._settings.update(settings)
        self._app_model.model_changed()
        # Settings can change the component sizes
        self._app_model.objects.components.update_sizes()
        self._app_model.sig_repaint.emit()

    def get_all(self):
        """Return settings dict"""
        return self._settings.copy()

    def from_dict(self, circuit_dict):
        """Get settings from circuit dict"""
        for key, data in circuit_dict.items():
            self._settings[key] = data

    def get(self, key):
        """Get model setting"""
        return self._settings.get(key)
