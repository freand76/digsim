# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Handle objects in the model"""

from digsim.circuit import Circuit
from digsim.circuit.components.atoms import DigsimException
from digsim.storage_model import AppFileDataClass, ModelDataClass

from ._model_components import ModelComponents
from ._model_new_wire import NewWire


class ModelObjects:
    """Class to handle objects in the model"""

    def __init__(self, app_model):
        self._app_model = app_model
        self._circuit = Circuit(name="DigSimCircuit")
        self._model_components = ModelComponents(app_model, self._circuit)
        self._undo_stack = []
        self._redo_stack = []
        self._new_wire = NewWire(self._app_model)

    @property
    def circuit(self):
        """return the model circuit"""
        return self._circuit

    @property
    def components(self):
        """return the model components"""
        return self._model_components

    @property
    def new_wire(self):
        """return the model components"""
        return self._new_wire

    def init(self):
        """Initialize objects"""
        self._model_components.init()

    def clear(self):
        """Clear components and wires"""
        self._model_components.clear()
        self._circuit.clear()

    def get_list(self):
        """Get list of all model objects"""
        model_objects = self._model_components.get_object_list()
        return model_objects

    def get_selected(self):
        """Get selected objects"""
        return [obj for obj in self.get_list() if obj.selected]

    def _delete(self, selected_objects):
        for obj in selected_objects:
            if ModelComponents.is_component_object(obj):
                self._model_components.delete(obj)

    def delete_selected(self):
        """Delete selected object(s)"""
        self.push_undo_state()
        selected_objects = self._app_model.objects.get_selected()
        if len(selected_objects) > 0:
            self._delete(selected_objects)
            self._app_model.model_changed()
        self._app_model.sig_delete_wires.emit()

    def model_to_circuit(self, model_dc, circuit_folder):
        if isinstance(model_dc, AppFileDataClass):
            # Loaded model
            dc = ModelDataClass.from_app_file_dc(model_dc)
        else:
            dc = model_dc

        try:
            # Create circuit
            exception_str_list = self.circuit.from_dataclass(
                dc.circuit,
                circuit_folder,
                component_exceptions=False,
                connect_exceptions=False,
            )
            # Add component positions
            self.components.add_gui_positions(dc.gui)
        except DigsimException as exc:
            self.sig_error.emit(f"Circuit error: {str(exc)}")
            return exception_str_list
        return exception_str_list

    def circuit_to_model(self, circuit_folder):
        model_dc = ModelDataClass(
            circuit=self.circuit.to_dataclass(circuit_folder), gui=self.components.get_gui_dict()
        )
        return model_dc

    def _restore_state(self, model_dc):
        self.clear()
        exception_str_list = self.model_to_circuit(model_dc, None)
        self._app_model.model_init()
        self._app_model.model_changed()
        if len(exception_str_list) > 0:
            self.sig_warning_log.emit("Load Circuit Warning", "\n".join(exception_str_list))

    def reset_undo_stack(self):
        """Clear undo/redo stacks"""
        self._undo_stack = []
        self._redo_stack = []
        self._app_model.sig_control_notify.emit()

    def push_undo_state(self, clear_redo_stack=True):
        """Push undo state to stack"""
        self._undo_stack.append(self.circuit_to_model("/"))
        if clear_redo_stack:
            self._redo_stack = []
            self._app_model.sig_control_notify.emit()

    def drop_undo_state(self):
        """Drop last undo state"""
        if len(self._undo_stack) > 0:
            self._undo_stack.pop()
            self._app_model.sig_control_notify.emit()

    def push_redo_state(self):
        """Push redo state to stack"""
        self._redo_stack.append(self.circuit_to_model("/"))

    def undo(self):
        """Undo to last saved state"""
        if len(self._undo_stack) > 0:
            self.push_redo_state()
            model_dc = self._undo_stack.pop()
            self._restore_state(model_dc)
            self._app_model.sig_control_notify.emit()
            self._app_model.sig_synchronize_gui.emit()

    def redo(self):
        """Undo to last saved state"""
        if len(self._redo_stack) > 0:
            self.push_undo_state(clear_redo_stack=False)
            model_dc = self._redo_stack.pop()
            self._restore_state(model_dc)
            self._app_model.sig_control_notify.emit()
            self._app_model.sig_synchronize_gui.emit()

    def can_undo(self):
        """Return true if the undo stack is not empty"""
        return len(self._undo_stack) > 0

    def can_redo(self):
        """Return true if the undo stack is not empty"""
        return len(self._redo_stack) > 0
