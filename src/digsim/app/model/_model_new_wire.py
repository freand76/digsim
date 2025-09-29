# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Handle new wire object in the model"""

from digsim.circuit.components.atoms import PortConnectionError


class NewWire:
    """Class to handle functionality for making a new wire"""

    def __init__(self, app_model):
        self._app_model = app_model
        self._start_port = None
        self._end_pos = None

    def start_port(self):
        """Get start port for unfinished new wire object"""
        return self._start_port

    def end_pos(self):
        """Get end point for unfinished new wire object"""
        return self._end_pos

    def start(self, component, portname):
        """Start new wire object"""
        if component.port(portname).can_add_wire():
            self._start_port = component.port(portname)

    def end(self, component, portname):
        """End new wire object"""
        end_port = component.port(portname)
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

    def abort(self):
        """Abort new wire object"""
        self._start_port = None
        self._end_pos = None

    def set_end_pos(self, pos):
        """Update end point for unfinished new wire object"""
        self._end_pos = pos

    def ongoing(self):
        """Return True if an unfinished new wire object is active"""
        return self._start_port is not None
