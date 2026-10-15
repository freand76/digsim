# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Handle settings in the model"""

from __future__ import annotations

import typing
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from ._model import AppModel


class ModelSettings:
    """Class to handle settings in the model"""

    DEFAULT_SETTINGS: typing.ClassVar[dict[str, Any]] = {
        # Slow down the simulation to real time
        "real_time": True,
        # Color wires by their logic level
        "color_wires": True,
        # GUI updates per second
        "update_frequency": 20,
    }

    def __init__(self, app_model: AppModel) -> None:
        self._app_model = app_model
        self._settings = dict(self.DEFAULT_SETTINGS)

    def update(self, settings: dict[str, Any]) -> None:
        """Update model settings"""
        self._settings.update(settings)
        self._app_model.model_changed()
        # Settings can change the component sizes
        self._app_model.objects.components.update_sizes()
        self._app_model.sig_repaint.emit()

    def get_all(self) -> dict[str, Any]:
        """Return settings dict"""
        return self._settings.copy()

    def from_dict(self, circuit_dict: dict[str, Any]) -> None:
        """
        Get settings from circuit dict. Unknown settings, and values that can't be used
        (like an update frequency of 0 in an edited file), are ignored.
        """
        for key, data in circuit_dict.items():
            default = self.DEFAULT_SETTINGS.get(key)
            if default is None or type(data) is not type(default):
                continue
            if key == "update_frequency" and data <= 0:
                continue
            self._settings[key] = data

    def get(self, key: str) -> Any:
        """Get model setting"""
        return self._settings.get(key)
