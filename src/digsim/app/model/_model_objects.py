# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

"""Handle objects in the model"""

# pylint: disable=too-many-public-methods

from digsim.circuit import Circuit
from digsim.circuit.components.atoms import DigsimException

from ._model_components import ModelComponents
from ._model_wires import ModelWires


class ModelObjects:
    """Class to objects in the model"""

    def __init__(self, app_model):
        self._app_model = app_model
        self._circuit = Circuit(name="DigSimCircuit")
        self._model_components = ModelComponents(app_model, self._circuit)
        self._model_wires = ModelWires(app_model, self._circuit)
        self._multi_select = False
        self._undo_stack = []
        self._redo_stack = []

    @property
    def circuit(self):
        """return the model circuit"""
        return self._circuit

    @property
    def components(self):
        """return the model components"""
        return self._model_components

    @property
    def wires(self):
        """return the model components"""
        return self._model_wires

    def multi_select_ongoing(self):
        """return True if multi select is ongoing"""
        return self._multi_select

    def init(self):
        """Initialize objects"""
        self._model_components.init()

    def clear(self):
        """Clear components and wires"""
        self._model_components.clear()
        self._model_wires.clear()
        self._circuit.clear()

    def get_list(self):
        """Get list of all model objects"""
        model_objects = self._model_components.get_object_list()
        model_objects.extend(self._model_wires.get_object_list())
        return model_objects

    def get_selected(self):
        """Get selected objects"""
        objects = []
        for obj in self.get_list():
            if obj.selected:
                objects.append(obj)
        return objects

    def multi_select(self, multi_select):
        """Enable/Disable multiple select of objects"""
        self._multi_select = multi_select

    def select(self, model_object=None):
        """Select model object"""
        if model_object is not None and model_object.selected:
            return
        for comp in self.get_list():
            if comp == model_object:
                comp.select(True)
            elif not self._multi_select:
                comp.select(False)
        self._app_model.sig_control_notify.emit()

    def select_by_position(self, pos):
        """Select object from position"""
        self.select(None)
        object_selected = self._model_wires.select(pos, self._multi_select)
        self._app_model.sig_control_notify.emit()
        return object_selected

    def select_by_rect(self, rect):
        """Select object be rectangle"""
        self.select(None)
        for obj in self.get_list():
            if obj.in_rect(rect):
                obj.select(True)
        self._app_model.sig_control_notify.emit()

    def move_selected_components(self, delta_pos, finalize=False):
        """Move selected objects"""
        if finalize:
            self.push_undo_state()
        selected_objects = self.get_selected()
        has_movement = False
        for obj in selected_objects:
            if ModelComponents.is_component_object(obj):
                if obj.move_delta(delta_pos, finalize=finalize):
                    has_movement = True
                obj.update()
                self._model_wires.update()
        if finalize:
            if has_movement:
                self._app_model.model_changed()
            else:
                # No movement, drop undo state
                self.drop_undo_state()
            self._app_model.sig_synchronize_gui.emit()
        return has_movement

    def _delete(self, selected_objects):
        for obj in selected_objects:
            if ModelComponents.is_component_object(obj):
                self._model_components.delete(obj)
        for obj in selected_objects:
            if ModelWires.is_wire_object(obj):
                self._model_wires.delete(obj)
        self._app_model.model_changed()
        self._app_model.sig_synchronize_gui.emit()

    def delete_selected(self):
        """Delete selected object(s)"""
        self.push_undo_state()
        selected_objects = self._app_model.objects.get_selected()
        if len(selected_objects) > 0:
            self._delete(selected_objects)

    def has_selection(self):
        """Return True if anything is selected"""
        return len(self.get_selected()) > 0

    def circuit_to_dict(self, circuit_folder):
        """Convert circuit and objects to dict"""
        circuit_dict = self.circuit.to_dict(circuit_folder)
        model_components_dict = self.components.get_circuit_dict()
        circuit_dict.update(model_components_dict)
        return circuit_dict

    def dict_to_circuit(self, circuit_dict, circuit_folder):
        """Convert dict to circuit and objects"""
        exception_str_list = []
        try:
            exception_str_list = self.circuit.from_dict(
                circuit_dict, circuit_folder, component_exceptions=False, connect_exceptions=False
            )
        except DigsimException as exc:
            self.sig_error.emit(f"Circuit error: {str(exc)}")
            return exception_str_list

        # Create GUI components
        self.components.create_from_dict(circuit_dict)
        # Create GUI wires
        self.wires.create_circuit_wires()

        return exception_str_list

    def _restore_state(self, state):
        self.clear()
        exception_str_list = self.dict_to_circuit(state, "/")
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
        self._undo_stack.append(self.circuit_to_dict("/"))
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
        self._redo_stack.append(self.circuit_to_dict("/"))

    def undo(self):
        """Undo to last saved state"""
        if len(self._undo_stack) > 0:
            self.push_redo_state()
            state = self._undo_stack.pop()
            self._restore_state(state)
            self._app_model.sig_control_notify.emit()
            self._app_model.sig_synchronize_gui.emit()

    def redo(self):
        """Undo to last saved state"""
        if len(self._redo_stack) > 0:
            self.push_undo_state(clear_redo_stack=False)
            state = self._redo_stack.pop()
            self._restore_state(state)
            self._app_model.sig_control_notify.emit()
            self._app_model.sig_synchronize_gui.emit()

    def can_undo(self):
        """Return true if the undo stack is not empty"""
        return len(self._undo_stack) > 0

    def can_redo(self):
        """Return true if the undo stack is not empty"""
        return len(self._redo_stack) > 0
