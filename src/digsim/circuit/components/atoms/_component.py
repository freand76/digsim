# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""This module contains the base classes for all component types"""

from __future__ import annotations

import abc
import copy
from typing import Callable

from ._digsim_exception import DigsimException
from ._port import Port


class ComponentException(DigsimException):
    """Component error exception class"""


class Component(abc.ABC):
    """The component base class"""

    def __init__(self, circuit, name: str | None = None, display_name: str | None = None):
        self._circuit = circuit
        self._name: str = name or self.__class__.__name__
        self._parent: Component | None = None
        self._ports: list[Port] = []
        self._circuit.add_component(self)
        self._display_name: str = display_name or self.__class__.__name__
        self._parameters: dict[str, int | str | bool] = {}

    def init(self):
        """Initialize port, will be called when circuit is initialized"""
        for port in self._ports:
            port.init()

    def default_state(self):
        """Setup default state, for example port outputs"""

    def clear(self):
        """Remove static state within the component class"""

    def parameter_set(self, parameter: str, value: int | str | bool):
        """Set component parameter"""
        self._parameters[parameter] = value

    def parameter_get(self, parameter: str) -> int | str | bool:
        """Get component parameter"""
        return self._parameters[parameter]

    def add_port(self, port: Port):
        """
        Add port to component,
        also add a 'portname' variable to the component with help of the 'self.__dict__'
        """
        self.__dict__[port.name()] = port
        self._ports.append(port)

    def delete_all_ports(self):
        """
        Deleta all component ports
        """
        self._ports = []

    def path(self) -> str:
        """Get component path (iterative)"""
        path_parts = []
        current_component = self
        while current_component is not None:
            name = current_component.name()
            if not isinstance(name, str):
                raise TypeError(
                    f"Component name is not a string: "
                    f"{name} ({type(name)}), "
                    f"component: {current_component.__class__.__name__}"
                )
            path_parts.append(name)
            current_component = current_component._parent
        return ".".join(reversed(path_parts))

    @property
    def ports(self):
        """Get component ports"""
        return self._ports

    def _get_ports(self, output) -> list[Port]:
        sel_ports = []
        for port in self._ports:
            if port.is_output() == output:
                sel_ports.append(port)
        return sel_ports

    def inports(self) -> list[Port]:
        """Get component input ports"""
        return self._get_ports(False)

    def outports(self) -> list[Port]:
        """Get component output ports"""
        return self._get_ports(True)

    def port(self, portname: str) -> Port:
        """Get port with name 'portname'"""
        for port in self._ports:
            if port.name() == portname:
                return port
        raise ComponentException(f"Port '{self.name()}:{portname}' not found")

    @property
    def circuit(self):
        """Get the circuit for the current component"""
        return self._circuit

    def name(self) -> str:
        """Get the component name"""
        return self._name

    def set_name(self, name: str, update_circuit: bool = True):
        """Set the component name"""
        if update_circuit:
            self.circuit.change_component_name(self, name)
        else:
            self._name = name

    def display_name(self) -> str:
        """Get the component display name"""
        return self._display_name

    def set_display_name(self, display_name: str):
        """Set the component display name"""
        self._display_name = display_name

    @property
    def parent(self) -> Component | None:
        """Get parent component"""
        return self._parent

    @parent.setter
    def parent(self, parent: Component):
        """Set component parent"""
        self._parent = parent

    def is_toplevel(self) -> bool:
        """Return True if this component is a toplevel component"""
        return self._parent is None

    @property
    def wire(self):
        """Property needed to be able to have a setter"""
        raise ComponentException(f"Cannot get wire for component '{self.display_name}'")

    @wire.setter
    def wire(self, port: Port):
        """Some components have a single output port, they can wired at component level"""
        self.outports()[0].wire = port

    def update(self):
        """This function is called if a port change and that port should update its parent"""

    def remove_connections(self):
        """Remove component connections"""
        for src_port in self.outports():
            for dst_port in src_port.wired_ports:
                dst_port.set_driver(None)

        for dst_port in self.inports():
            if dst_port.has_driver():
                dst_port.get_driver().disconnect(dst_port)

    def add_event(self, port: Port, value: int, delay_ns: int):
        """Add delta cycle event"""
        self.circuit.add_event(port, value, delay_ns)

    def __str__(self):
        comp_str = f"{self.display_name()}"
        for port in self.inports():
            comp_str += f"\n - I:{port.name()}={port.value}"
        for port in self.outports():
            comp_str += f"\n - O:{port.name()}={port.value}"
        return comp_str

    @property
    def has_action(self) -> bool:
        """Return True if this component is interactive"""
        return False

    @property
    def active(self) -> bool:
        """Return True if this component is active/activated ('on' for a switch for example)"""
        return False

    def onpress(self):
        """What to happen for an interactive activation"""

    def onrelease(self):
        """What to happen for an interactive de-activation"""

    def settings_from_dict(self, settings):
        """Get component settings from dict"""
        raise ComponentException(f"No setup for component '{self.display_name}'")

    def settings_to_dict(self) -> dict[str, int | str | bool]:
        """Return component settings as a dict"""
        return copy.deepcopy(self._parameters)

    @classmethod
    def get_parameters(cls):
        """Return parameters"""
        return {}

    def update_settings(self, settings: dict[str, int | str | bool]):
        """Update parameters from settings dict"""
        for setting, value in settings.items():
            self.parameter_set(setting, value)
            self.reconfigure()

    def reconfigure(self):
        """Update the component from the parameters"""

    def get_reconfigurable_parameters(self):
        """Return reconfigurable parameters"""
        reconfigurable_parameters = {}
        for parameter, parameter_dict in self.get_parameters().items():
            if parameter_dict.get("reconfigurable", False):
                reconfigurable_parameters[parameter] = copy.deepcopy(parameter_dict)
                reconfigurable_parameters[parameter]["default"] = self.parameter_get(parameter)
                if reconfigurable_parameters[parameter]["type"] == "width_pow2":
                    reconfigurable_parameters[parameter]["type"] = int
                    reconfigurable_parameters[parameter]["min"] = 0
                    reconfigurable_parameters[parameter]["max"] = (
                        2 ** self.parameter_get("width") - 1
                    )
        return reconfigurable_parameters


class MultiComponent(Component):
    """A component that holds one or several sub components"""

    def __init__(self, circuit, name: str):
        super().__init__(circuit, name)
        self._components: list[Component] = []

    def init(self):
        super().init()
        for component in self._components:
            component.init()

    def remove_all_components(self):
        """Remove all sub components from multicomponent"""
        self._components = []

    def default_state(self):
        super().default_state()
        for component in self._components:
            component.default_state()

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

    def __init__(self, circuit, name: str, callback: Callable[[Component], None] | None = None):
        super().__init__(circuit, name)
        self._callback = callback

    def set_callback(self, callback: Callable[[Component], None]):
        """Set CallbackComponent callback function"""
        self._callback = callback

    def update(self):
        """Call CallbackComponent callback function if available"""
        if self._callback is not None:
            self._callback(self)
