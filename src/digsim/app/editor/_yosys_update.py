# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""Update the Yosys components of a file with new netlists, and ask first if ports change"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMessageBox, QWidget

from digsim.app._yosys_interface import YosysUpdate, change_message


if TYPE_CHECKING:
    from digsim.app.model import AppModel


def update_yosys_components(
    parent: QWidget | None, app_model: AppModel, update: YosysUpdate
) -> bool:
    """
    Build the Yosys components of a file from new netlists (see prepare_yosys_update). If
    their ports change, ask first. Returns False if that was cancelled.
    """
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
    warnings = app_model.objects.components.apply_yosys_update(update)
    if warnings:
        app_model.sig_warning_log.emit("Yosys Component Warning", "\n".join(warnings))
    return True
