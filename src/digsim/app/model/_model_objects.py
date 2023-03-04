# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

"""Handle objects in the model"""

from digsim.circuit import Circuit

from ._model_components import ModelComponents
from ._model_wires import ModelWires


class ModelObjects:
    """Class to objects in the model"""

    def __init__(self, app_model):
        self._app_model = app_model
        self._circuit = Circuit(name="DigSimCircuit", vcd="gui.vcd")
        self._model_components = ModelComponents(app_model, self._circuit)
        self._model_wires = ModelWires(app_model)
        self._multi_select = False

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

    def init(self):
        """Initialize objects"""
        self._model_components.init()

    def clear(self):
        """Clear components and wires"""
        self._model_components.clear()
        self._model_wires.clear()

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
        self._app_model.sig_update_gui_components.emit()

    def select_by_position(self, pos):
        """Select object from position"""
        self.select(None)
        object_selected = self._model_wires.select(pos, self._multi_select)
        if object_selected:
            self._app_model.sig_control_notify.emit()
        return object_selected

    def select_by_rect(self, rect):
        """Select object be rectangle"""
        self.select(None)
        for obj in self.get_list():
            if obj.in_rect(rect):
                obj.select(True)

    def move_selected_components(self, delta_pos):
        """Move selected objects"""
        selected_objects = self.get_selected()
        for obj in selected_objects:
            if ModelComponents.is_component_object(obj):
                obj.move_delta(delta_pos)
                obj.update()
                self._model_wires.update()
                self._app_model.model_changed(update_components=False)

    def delete(self, selected_objects):
        """Delete selected object(s)"""
        for obj in selected_objects:
            if ModelComponents.is_component_object(obj):
                self._model_components.delete(obj)
        for obj in selected_objects:
            if ModelWires.is_wire_object(obj):
                self._model_wires.delete(obj)
        self._app_model.model_changed()
        self._app_model.sig_update_gui_components.emit()

    def has_selection(self):
        """Return True if anything is selected"""
        return len(self.get_selected()) > 0
