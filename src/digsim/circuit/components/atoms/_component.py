# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

# pylint: disable=too-many-public-methods

import abc
import importlib

from ._enum import PortDirection


class ComponentException(Exception):
    pass


class Component(abc.ABC):
    def __init__(self, circuit, name="", display_name=None):
        self._circuit = circuit
        self._name = name
        self._parent = None
        self._ports = []
        self._circuit.add_component(self)
        self._display_name = display_name or self.__class__.__name__

    def init(self):
        for port in self._ports:
            port.init()

    def add_port(self, port):
        self.__dict__[port.name] = port
        self._ports.append(port)

    @property
    def path(self):
        if self._parent is not None:
            return f"{self._parent.path}.{self.name}"
        return f"{self.name}"

    @property
    def ports(self):
        return self._ports

    def _get_ports(self, direction):
        sel_ports = []
        for port in self._ports:
            if port.direction == direction:
                sel_ports.append(port)
        return sel_ports

    @property
    def inports(self):
        return self._get_ports(PortDirection.IN)

    @property
    def outports(self):
        return self._get_ports(PortDirection.OUT)

    def port(self, portname):
        for port in self._ports:
            if port.name == portname:
                return port
        raise ComponentException("Port not found")

    @property
    def circuit(self):
        return self._circuit

    @property
    def name(self):
        return self._name

    @property
    def display_name(self):
        return self._display_name

    @display_name.setter
    def display_name(self, display_name):
        self._display_name = display_name

    @property
    def parent(self):
        return self._parent

    def is_toplevel(self):
        return self._parent is None

    @parent.setter
    def parent(self, parent):
        self._parent = parent

    def update(self):
        pass

    def remove_connections(self):
        for src_port in self.outports:
            for dst_port in src_port.wires:
                dst_port.set_driver(None)

        for dst_port in self.inports:
            if dst_port.has_driver():
                dst_port.driver.disconnect(dst_port)

    def add_event(self, port, level, propagation_delay_ns):
        self.circuit.add_event(port, level, propagation_delay_ns)

    def __str__(self):
        comp_str = f"{self.display_name}"
        for port in self.inports:
            comp_str += f"\n - I:{port.name}={port.bitval}"
        for port in self.outports:
            comp_str += f"\n - O:{port.name}={port.bitval}"
        return comp_str

    def to_dict(self):
        component_dict = {
            "name": self.name,
            "display_name": self.display_name,
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
            component.settings_from_dict(component_settings)
        if display_name is not None:
            component.display_name = display_name
        return component

    @property
    def has_action(self):
        return False

    @property
    def active(self):
        return False

    def onpress(self):
        pass

    def onrelease(self):
        pass

    def settings_from_dict(self, settings):
        raise ComponentException(f"No setup for component '{self.display_name}'")

    def settings_to_dict(self):
        return {}


class MultiComponent(Component):
    def __init__(self, circuit, name):
        super().__init__(circuit, name)
        self._components = []

    def add(self, component):
        self._components.append(component)
        component.parent = self


class CallbackComponent(Component):
    def __init__(self, circuit, name, callback=None):
        super().__init__(circuit, name)
        self._callback = callback

    def set_callback(self, callback):
        self._callback = callback

    def update(self):
        if self._callback is not None:
            self._callback(self)
