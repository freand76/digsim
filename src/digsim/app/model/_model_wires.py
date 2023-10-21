# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

"""Handle wire objects in the model"""

from digsim.app.gui_objects import WireObject


class NewWire:
    """Class to handle functionality for making a new wire"""

    def __init__(self, app_model):
        self._app_model = app_model
        self._wire = None
        self._end_pos = None

    @property
    def wire(self):
        """Get unfinished new wire object"""
        return self._wire

    @property
    def end_pos(self):
        """Get end point for unfinished new wire object"""
        return self._end_pos

    def start(self, component, portname):
        """Start new wire object"""
        if component.port(portname).can_add_wire():
            self._wire = WireObject(self._app_model, component.port(portname))

    def end(self, component, portname):
        """End new wire object"""
        self._app_model.objects.push_undo_state()
        self._wire.set_end_port(component.port(portname))
        self._app_model.objects.wires.add_wire(self._wire)
        self._app_model.model_changed()
        self._wire = None
        self._end_pos = None

    def abort(self):
        """Abort new wire object"""
        self._wire = None
        self._end_pos = None

    def set_end_pos(self, pos):
        """Update end point for unfinished new wire object"""
        self._end_pos = pos

    def ongoing(self):
        """Return True if an unfinished new wire object is active"""
        return self._wire is not None


class ModelWires:
    """Class to handle the wire objects in the model"""

    @staticmethod
    def is_wire_object(obj):
        """Test if this object is a wire object"""
        return isinstance(obj, WireObject)

    def __init__(self, app_model, circuit):
        self._app_model = app_model
        self._circuit = circuit
        self._wire_objects = {}
        self._new_wire = NewWire(self._app_model)

    @property
    def new(self):
        """Get the new wire instance"""
        return self._new_wire

    def clear(self):
        """Clear wire objects"""
        self._wire_objects = {}

    def _add_object(self, src_port, dst_port, connect=True):
        """Add wire object between source and destination port"""
        wire = WireObject(self._app_model, src_port, dst_port, connect)
        self.add_wire(wire)

    def add_wire(self, wire):
        """Add wire object"""
        self._wire_objects[wire.key] = wire

    def get_object_list(self):
        """Get list of wire objects"""
        wire_objects = []
        for _, wire in self._wire_objects.items():
            wire_objects.append(wire)
        return wire_objects

    def update(self):
        """Update wire objects"""
        for _, wire in self._wire_objects.items():
            wire.update()

    def delete(self, wire_object):
        """Delete wire objects"""
        wire_object.disconnect()
        if wire_object.key in self._wire_objects:
            del self._wire_objects[wire_object.key]
        self._app_model.model_changed()

    def create_circuit_wires(self):
        """Create model wires from circuit"""
        for comp in self._circuit.get_toplevel_components():
            for src_port in comp.outports():
                for dst_port in src_port.get_wires():
                    self._add_object(src_port, dst_port, connect=False)
