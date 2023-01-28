# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

""" This module contains the base classes for all component types """


# pylint: disable=too-many-public-methods

import abc
import importlib


class ComponentException(Exception):
    """Component error exception class"""


class Component(abc.ABC):
    """The component base class"""

    def __init__(self, circuit, name="", display_name=None):
        self._circuit = circuit
        self._name = name
        self._parent = None
        self._ports = []
        self._edge_detect_dict = {}
        self._circuit.add_component(self)
        self._display_name = display_name or self.__class__.__name__

    def init(self):
        """Initialize port, will be called when circuit is initialized"""
        for port in self._ports:
            port.init()

    def add_port(self, port):
        """
        Add port to component,
        also add a 'portname' variable to the component with help of the 'self.__dict__'
        """
        self.__dict__[port.name()] = port
        self._ports.append(port)

    def path(self):
        """Get component path"""
        if self._parent is not None:
            return f"{self._parent.path()}.{self.name()}"
        return f"{self.name()}"

    @property
    def ports(self):
        """Get component ports"""
        return self._ports

    def _get_ports(self, output):
        sel_ports = []
        for port in self._ports:
            if port.is_output() == output:
                sel_ports.append(port)
        return sel_ports

    def inports(self):
        """Get component input ports"""
        return self._get_ports(False)

    def outports(self):
        """Get component output ports"""
        return self._get_ports(True)

    def port(self, portname):
        """Get port with name 'portname'"""
        for port in self._ports:
            if port.name() == portname:
                return port
        raise ComponentException(f"Port {self.name}:{portname} not found")

    @property
    def circuit(self):
        """Get the circuit for the current component"""
        return self._circuit

    def name(self):
        """Get the component name"""
        return self._name

    def set_name(self, name):
        """Set the component name"""
        self._name = name

    def display_name(self):
        """Get the component display name"""
        return self._display_name

    def set_display_name(self, display_name):
        """Set the component display name"""
        self._display_name = display_name

    @property
    def parent(self):
        """Get parent component"""
        return self._parent

    def is_toplevel(self):
        """Return True if this component is a toplevel component"""
        return self._parent is None

    @parent.setter
    def parent(self, parent):
        """Set component parent"""
        self._parent = parent

    @property
    def wire(self):
        """Property needed to be able to have a setter"""
        raise ComponentException(f"Cannot get wire for component '{self.display_name}'")

    @wire.setter
    def wire(self, port):
        """Some components have a single output port, they can wired at component level"""
        self.outports()[0].wire = port

    def update(self):
        """This function is called if a port change and that port should update its parent"""

    def remove_connections(self):
        """Remove component connections"""
        for src_port in self.outports():
            for dst_port in src_port.get_wires():
                dst_port.set_driver(None)

        for dst_port in self.inports():
            if dst_port.has_driver():
                dst_port.driver.disconnect(dst_port)

    def add_event(self, port, value, delay_ns):
        """Add delta cycle event"""
        self.circuit.add_event(port, value, delay_ns)

    def __str__(self):
        comp_str = f"{self.display_name()}"
        for port in self.inports():
            comp_str += f"\n - I:{port.name()}={port.value}"
        for port in self.outports():
            comp_str += f"\n - O:{port.name()}={port.value}"
        return comp_str

    def to_dict(self):
        """Return the component information as a dict, used when storing a circuit"""
        component_dict = {
            "name": self.name(),
            "display_name": self.display_name(),
        }

        module_split = type(self).__module__.split(".")
        type_str = ""
        for module in module_split:
            if not module.startswith("_"):
                type_str += f"{module}."
        type_str += type(self).__name__
        component_dict["type"] = type_str
        component_dict["settings"] = self.settings_to_dict()
        return component_dict

    @classmethod
    def from_dict(cls, circuit, json_component):
        """Factory: Create a component from a dict"""
        component_name = json_component["name"]
        component_type = json_component["type"]
        display_name = json_component.get("display_name")
        component_settings = json_component.get("settings")
        py_module_name = ".".join(component_type.split(".")[0:-1])
        py_class_name = component_type.split(".")[-1]

        module = importlib.import_module(py_module_name)
        class_ = getattr(module, py_class_name)
        component = class_(circuit=circuit, name=component_name)
        if component_settings is not None and bool(component_settings):
            component.setup(**component_settings)
        if display_name is not None:
            component.set_display_name(display_name)
        return component

    @property
    def has_action(self):
        """Return True if this component is interactive"""
        return False

    @property
    def active(self):
        """Return True if this component is active/activated ('on' for a switch for example)"""
        return False

    def onpress(self):
        """What to happen for an interactive activation"""

    def onrelease(self):
        """What to happen for an interactive de-activation"""

    def settings_from_dict(self, settings):
        """Get component settings from dict"""
        raise ComponentException(f"No setup for component '{self.display_name}'")

    def settings_to_dict(self):
        """Return component settings as a dict"""
        return {}


class MultiComponent(Component):
    """A component that holds one or several sub components"""

    def __init__(self, circuit, name):
        super().__init__(circuit, name)
        self._components = []

    def add(self, component):
        """Add sub-component to MultiComponent"""
        self._components.append(component)
        component.parent = self


class CallbackComponent(Component):
    """
    A component that will call a callback function upon change,
    this is used to for example output text in stdout or update GUI
    objects when the component change value.
    """

    def __init__(self, circuit, name, callback=None):
        super().__init__(circuit, name)
        self._callback = callback

    def set_callback(self, callback):
        """Set CallbackComponent callback function"""
        self._callback = callback

    def update(self):
        """Call CallbackComponent callback function if available"""
        if self._callback is not None:
            self._callback(self)
