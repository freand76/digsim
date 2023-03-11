# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

"""Handle settings in the model"""


class ModelSettings:
    """Class to handle settings in the model"""

    def __init__(self, app_model):
        self._app_model = app_model
        self._settings = {}

    def update(self, settings):
        """Update model settings"""
        self._settings.update(settings)
        self._app_model.model_changed()
        # Settings can change the component sizes
        self._app_model.objects.components.update_sizes()
        self._app_model.sig_synchronize_gui.emit()

    def get(self, key):
        """Get model setting"""
        return self._settings.get(key)
