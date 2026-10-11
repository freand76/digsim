# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Handle new wire object in the model"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QPointF

from digsim.circuit.components.atoms import Component, Port, PortConnectionError


if TYPE_CHECKING:
    from ._model import AppModel


class NewWire:
    """Class to handle functionality for making a new wire"""

    def __init__(self, app_model: AppModel) -> None:
        self._app_model = app_model
        self._start_port: Port | None = None
        self._end_pos: QPointF | None = None

    def start_port(self) -> Port | None:
        """Get start port for unfinished new wire object"""
        return self._start_port

    def end_pos(self) -> QPointF | None:
        """Get end point for unfinished new wire object"""
        return self._end_pos

    def start(self, component: Component, portname: str) -> None:
        """Start new wire object"""
        if component.port(portname).can_add_wire():
            self._start_port = component.port(portname)

    def end(self, component: Component, portname: str) -> None:
        """End new wire object"""
        end_port = component.port(portname)
        if self._start_port is None:
            raise PortConnectionError("No wire started")
        if self._start_port.is_output() and end_port.is_input():
            self._app_model.objects.push_undo_state()
            self._start_port.wire = end_port
        elif self._start_port.is_input() and end_port.is_output():
            self._app_model.objects.push_undo_state()
            end_port.wire = self._start_port
        else:
            raise PortConnectionError("Cannot connect to port of same type")
        self._app_model.sig_update_wires.emit()
        self._app_model.model_changed()
        self._start_port = None
        self._end_pos = None

    def abort(self) -> None:
        """Abort new wire object"""
        self._start_port = None
        self._end_pos = None

    def set_end_pos(self, pos: QPointF) -> None:
        """Update end point for unfinished new wire object"""
        self._end_pos = pos

    def ongoing(self) -> bool:
        """Return True if an unfinished new wire object is active"""
        return self._start_port is not None
