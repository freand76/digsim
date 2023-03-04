# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

"""Handle component objects in the model"""

import digsim.circuit.components
from digsim.circuit.components.atoms import CallbackComponent


class ModelComponents:
    """Class to handle the component objects in the model"""

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
        for _, comp in self._component_objects.items():
            self._app_model.sig_component_notify.emit(comp.component)

    def has_objects(self):
        """Return True if there are component objects in the model"""
        return len(self._component_objects) > 0

    def update_callback_components(self):
        """
        Update the GUI for the components that have changed since the last call
        """
        for comp in self._component_callback_list:
            self._app_model.sig_component_notify.emit(comp)
        self._component_callback_list = []

    def _component_callback(self, component):
        """Add component to callback list (if not available)"""
        if component not in self._component_callback_list:
            self._component_callback_list.append(component)

    def get_component_object(self, component):
        """Get component object (from component)"""
        return self._component_objects[component]

    def _get_component_class(self, name):
        return getattr(digsim.circuit.components, name)

    def get_component_parameters(self, name):
        """Get parameters for a component"""
        return self._get_component_class(name).get_parameters()

    def add_component_by_name(self, name, pos, settings):
        """Add component object from class name"""
        component_class = self._get_component_class(name)
        component = component_class(self._circuit, **settings)
        self._app_model.circuit_init()
        component_object = self.add_component(component, pos.x(), pos.y())
        component_object.center()  # Component is plced @ mouse pointer, make it center
        self._app_model.model_changed()
        return component_object

    def add_component(self, component, xpos, ypos):
        """Add component object in position"""
        component_object_class = digsim.app.gui_objects.class_factory(type(component).__name__)
        self._component_objects[component] = component_object_class(
            self._app_model, component, xpos, ypos
        )
        if isinstance(component, CallbackComponent):
            component.set_callback(self._component_callback)
        return self._component_objects[component]

    def get_component_objects(self):
        """Get list of component objects"""
        component_objects = []
        for _, comp in self._component_objects.items():
            component_objects.append(comp)
        return component_objects

    def delete_component(self, component_object):
        """Deleta a component object in the model"""
        for port in component_object.component.ports:
            for wire in self.get_wire_objects():
                if wire.has_port(port):
                    self._delete_wire(wire)
        del self._component_objects[component_object.component]
        self._circuit.delete_component(component_object.component)
