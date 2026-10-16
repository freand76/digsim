# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""A component context menu"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QPoint
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QWidget

from digsim.app.settings import ComponentSettingsDialog
from digsim.circuit.components.atoms import Parameter


if TYPE_CHECKING:
    from digsim.app.model import AppModel

    from ._component_object import ComponentObject


class ComponentContextMenu(QMenu):
    """The component contextmenu class"""

    def __init__(
        self, parent: QWidget | None, app_model: AppModel, component_object: ComponentObject
    ) -> None:
        super().__init__(parent)
        self._parent = parent
        self._app_model = app_model
        self._component_object = component_object
        self._component = self._component_object.component
        self._reconfigurable_parameters: dict[str, Parameter] = {}
        # Title
        titleAction = QAction(self._component.display_name(), self)
        titleAction.setEnabled(False)
        self.addAction(titleAction)
        self.addSeparator()
        # Settings
        self._add_settings()
        self._component_object.add_context_menu_action(self, parent)
        self.addSeparator()
        # Bring to front / Send to back
        raiseAction = QAction("Bring to front", self)
        self.addAction(raiseAction)
        raiseAction.triggered.connect(self._raise)
        lowerAction = QAction("Send to back", self)
        self.addAction(lowerAction)
        lowerAction.triggered.connect(self._lower)
        self.addSeparator()
        # Delete
        deleteAction = QAction("Delete", self)
        self.addAction(deleteAction)
        deleteAction.triggered.connect(self._delete)

    def _add_settings(self) -> None:
        self._reconfigurable_parameters = self._component.get_reconfigurable_parameters()
        if len(self._reconfigurable_parameters) > 0:
            settingsAction = QAction("Settings", self)
            self.addAction(settingsAction)
            settingsAction.triggered.connect(self._settings)

    def open_at(self, position: QPoint) -> None:
        """Create context menu for component"""
        self.exec(position)

    def _delete(self) -> None:
        self._component_object.setSelected(True)
        self._app_model.objects.delete_selected()

    def _raise(self) -> None:
        self._app_model.objects.components.bring_to_front(self._component_object)

    def _lower(self) -> None:
        self._app_model.objects.components.send_to_back(self._component_object)

    def _settings(self) -> None:
        """Start the settings dialog for reconfiguration"""
        ok, settings = ComponentSettingsDialog.start(
            self._parent,
            self._app_model,
            self._component.name(),
            self._reconfigurable_parameters,
        )
        if ok:
            self._app_model.objects.components.update_settings(self._component_object, settings)
