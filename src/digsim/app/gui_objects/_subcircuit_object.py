# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""A subcircuit placed in the GUI"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QMessageBox, QWidget

from digsim.app._yosys_interface import change_message
from digsim.circuit.components import SubCircuit
from digsim.circuit.components.atoms import DigsimException

from ._named_box_object import NamedBoxObject


if TYPE_CHECKING:
    from digsim.app.model import AppModel


def reload_subcircuits(parent: QWidget | None, app_model: AppModel, path: str) -> bool:
    """
    Build the subcircuits of a file again from it. If their ports change, ask first.
    Returns False if that was cancelled, or the file can't be read.
    """
    components = app_model.objects.components
    try:
        update = components.prepare_subcircuit_reload(path)
    except DigsimException as exc:
        app_model.sig_warning_log.emit("Reload Subcircuit Warning", str(exc))
        return False
    if update.ports_change():
        answer = QMessageBox.warning(
            parent,
            "Ports change",
            change_message(update.names(), update.port_changes(), update.removed),
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Ok:
            return False
    warnings = components.apply_subcircuit_reload(update)
    if warnings:
        app_model.sig_warning_log.emit("Subcircuit Warning", "\n".join(warnings))
    return True


class SubCircuitObject(NamedBoxObject):
    """A subcircuit: a body with the name of its file and the names of its ports"""

    ICON_TEXT = "Circuit"

    @property
    def component(self) -> SubCircuit:
        component = self._component
        assert isinstance(component, SubCircuit)
        return component

    def add_context_menu_action(self, menu: QMenu, parent: QWidget | None) -> None:
        reload_action = QAction("Reload", menu)
        menu.addAction(reload_action)
        reload_action.triggered.connect(
            lambda: reload_subcircuits(parent, self._app_model, str(self.component.source_file()))
        )
