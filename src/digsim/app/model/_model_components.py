# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Handle component objects in the model"""

import digsim.circuit.components
from digsim.app.gui_objects import ComponentObject
from digsim.circuit.components import Buzzer
from digsim.circuit.components.atoms import CallbackComponent
from digsim.storage_model import GuiPositionDataClass


class ModelComponents:
    """Class to handle the component objects in the model"""

    @staticmethod
    def is_component_object(obj):
        """Test if this object is a component object"""
        return isinstance(obj, ComponentObject)

    def __init__(self, app_model, circuit):
        self._app_model = app_model
        self._circuit = circuit
        self._component_objects = {}
        self._component_callback_list = []

    def clear(self):
        """Clear components objects"""
        self._component_objects = {}

    def init(self):
        """Initialize components objects"""
        self._app_model.sig_repaint.emit()

    def get_dict(self):
        """Get component objects dict"""
        return self._component_objects

    def is_empty(self):
        """Return True if there are component objects in the model"""
        return len(self._component_objects) == 0

    def get_top_zlevel(self):
        """Get thehighest z level in the model"""
        max_zlevel = None
        for _, comp_object in self._component_objects.items():
            max_zlevel = (
                comp_object.zlevel if max_zlevel is None else (max(max_zlevel, comp_object.zlevel))
            )
        return max_zlevel

    def component_moved(self):
        """Call when component has moved to update state"""
        self._app_model.objects.push_undo_state()
        self._app_model.model_changed()

    def bring_to_front(self, component_object):
        """Make the component object the highest in the stack"""
        max_zlevel = self.get_top_zlevel()
        component_object.zlevel = max_zlevel + 1
        self._app_model.model_changed()

    def send_to_back(self, component_object):
        """Make the component object the lowest in the stack"""
        min_zlevel = None
        for _, comp_object in self._component_objects.items():
            min_zlevel = (
                comp_object.zlevel if min_zlevel is None else (min(min_zlevel, comp_object.zlevel))
            )
        if min_zlevel == 0:
            for _, comp_object in self._component_objects.items():
                comp_object.zlevel = comp_object.zlevel + 1
            component_object.zlevel = 0
        else:
            component_object.zlevel = min_zlevel - 1
        self._app_model.model_changed()

    def update_callback_objects(self):
        """
        Update the GUI for the components that have changed since the last call
        """
        if len(self._component_callback_list) == 0:
            return
        for comp in self._component_callback_list:
            if isinstance(comp, Buzzer):
                self._app_model.sig_audio_notify.emit(comp)
        self._app_model.sig_repaint.emit()
        self._component_callback_list = []

    def _component_callback(self, component):
        """Add component to callback list (if not available)"""
        if component not in self._component_callback_list:
            self._component_callback_list.append(component)

    def _get_component_class(self, name):
        return getattr(digsim.circuit.components, name)

    def get_object_parameters(self, name):
        """Get parameters for a component"""
        return self._get_component_class(name).get_parameters()

    def _add_object(self, component, xpos, ypos):
        """Add component object in position"""
        component_object_class = digsim.app.gui_objects.class_factory(type(component).__name__)
        self._component_objects[component] = component_object_class(
            self._app_model, component, xpos, ypos
        )
        if isinstance(component, CallbackComponent):
            component.set_callback(self._component_callback)
        return self._component_objects[component]

    def add_object_by_name(self, name, pos, settings):
        """Add component object from class name"""
        self._app_model.objects.push_undo_state()
        component_class = self._get_component_class(name)
        component = component_class(self._circuit, **settings)
        self._app_model.model_init()
        component_object = self._add_object(component, pos.x(), pos.y())
        self._app_model.model_changed()
        return component_object

    def get_object(self, component):
        """Get component object (from component)"""
        return self._component_objects[component]

    def get_object_list(self):
        """Get list of component objects"""
        return list(self._component_objects.values())

    def update_settings(self, component_object, settings):
        """Update settings for a component"""
        self._app_model.objects.push_undo_state()
        component_object.component.update_settings(settings)
        self._app_model.model_changed()
        # Settings can change the component size
        component_object.update_size()
        self._app_model.sig_repaint.emit()

    def update_sizes(self):
        """Update all component sizes"""
        for comp_object in self.get_object_list():
            comp_object.update_size()

    def delete(self, component_object):
        """Delete a component object in the model"""
        del self._component_objects[component_object.component]
        self._circuit.delete_component(component_object.component)
        self._app_model.sig_delete_component.emit(component_object)

    def add_gui_positions(self, gui_dc_dict):
        """Create model components from circuit_dict"""
        for comp in self._circuit.get_toplevel_components():
            gui_dc = gui_dc_dict.get(comp.name(), GuiPositionDataClass())
            component_object = self._add_object(comp, gui_dc.x, gui_dc.y)
            component_object.zlevel = gui_dc.z

    def get_gui_dict(self):
        """Return gui dict from component objects"""
        gui_dict = {}
        for comp, comp_object in self.get_dict().items():
            gui_dict[comp.name()] = comp_object.to_gui_dataclass()
        return gui_dict
