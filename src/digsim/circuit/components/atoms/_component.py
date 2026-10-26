# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""This module contains the base classes for all component types"""

from __future__ import annotations

import abc
import copy
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Literal, NoReturn, NotRequired, TypedDict

from ._digsim_exception import DigsimException
from ._port import VALUE_TYPE, Port, PortInOut, PortMultiBitWire, PortOutDelta


if TYPE_CHECKING:
    from digsim.circuit import Circuit

ParameterValue = int | str | bool | list[int] | None

# The settings input for a parameter, see "The settings dialog" in docs/gui-components.md
ParameterType = Literal[
    "bool",
    "component_name",
    "ic_name",
    "int",
    "intrange",
    "list",
    "path",
    "str",
    "width_bool",
    "width_pow2",
]


class Parameter(TypedDict):
    """
    The description of a component parameter, returned by get_parameters(). The GUI
    builds the settings dialog from it, see "The settings dialog" in the guide for adding
    components to the GUI.
    """

    type: ParameterType
    description: str
    default: NotRequired[Any]
    min: NotRequired[int]
    max: NotRequired[int]
    reconfigurable: NotRequired[bool]
    single_line: NotRequired[bool]
    invalid_list: NotRequired[list[str]]
    items: NotRequired[list[str]]
    range: NotRequired[list[int]]
    default_index: NotRequired[int]
    component_list: NotRequired[dict[str, str]]
    fileinfo: NotRequired[str]
    # A new Verilog file can be made instead of opening one, it is created with a module
    new_verilog: NotRequired[bool]
    # Only asked when the file of the path parameter has one of these types, like ".v"
    file_types: NotRequired[list[str]]


class ComponentException(DigsimException):
    """Component error exception class"""


class Component(abc.ABC):
    """The component base class"""

    if TYPE_CHECKING:
        # Ports are added as instance attributes by add_port(), e.g. 'self.Y'
        def __getattr__(self, name: str) -> Port: ...

    def __init__(
        self, circuit: Circuit, name: str | None = None, display_name: str | None = None
    ) -> None:
        self._circuit = circuit
        self._name: str = name or self.__class__.__name__
        self._parent: Component | None = None
        self._ports: list[Port] = []
        self._circuit.add_component(self)
        self._display_name: str = display_name or self.__class__.__name__
        self._parameters: dict[str, ParameterValue] = {}

    def init(self) -> None:
        """Initialize port, will be called when circuit is initialized"""
        for port in self._ports:
            port.init()

    def default_state(self) -> None:
        """Setup default state, for example port outputs"""

    def clear(self) -> None:
        """Remove static state within the component class"""

    def parameter_set(self, parameter: str, value: ParameterValue) -> None:
        """Set component parameter"""
        self._parameters[parameter] = value

    def parameter_get(self, parameter: str) -> Any:
        """Get component parameter"""
        return self._parameters[parameter]

    def add_port(self, port: Port) -> None:
        """
        Add port to component,
        also add a 'portname' variable to the component with help of the 'self.__dict__'
        """
        self.__dict__[port.name()] = port
        self._ports.append(port)

    def path(self) -> str:
        """Get component path (iterative)"""
        path_parts = []
        current_component: Component | None = self
        while current_component is not None:
            path_parts.append(current_component.name())
            current_component = current_component._parent
        return ".".join(reversed(path_parts))

    @property
    def ports(self) -> list[Port]:
        """Get component ports"""
        return self._ports

    def _get_ports(self, output: bool) -> list[Port]:
        return [port for port in self._ports if port.is_output() == output]

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
    def circuit(self) -> Circuit:
        """Get the circuit for the current component"""
        return self._circuit

    def name(self) -> str:
        """Get the component name"""
        return self._name

    def set_name(self, name: str, update_circuit: bool = True) -> None:
        """Set the component name"""
        if update_circuit:
            self.circuit.change_component_name(self, name)
        else:
            self._name = name

    def display_name(self) -> str:
        """Get the component display name"""
        return self._display_name

    def set_display_name(self, display_name: str) -> None:
        """Set the component display name"""
        self._display_name = display_name

    @property
    def parent(self) -> Component | None:
        """Get parent component"""
        return self._parent

    @parent.setter
    def parent(self, parent: Component) -> None:
        """Set component parent"""
        self._parent = parent

    def is_toplevel(self) -> bool:
        """Return True if this component is a toplevel component"""
        return self._parent is None

    @property
    def wire(self) -> NoReturn:
        """Property needed to be able to have a setter"""
        raise ComponentException(f"Cannot get wire for component '{self.display_name()}'")

    @wire.setter
    def wire(self, port: Port) -> None:
        """Some components have a single output port, they can wired at component level"""
        self.outports()[0].wire = port

    def update(self) -> None:
        """This function is called if a port change and that port should update its parent"""

    def remove_connections(self) -> None:
        """Remove component connections"""
        for src_port in self.outports():
            # Also from the port's own list, or an event it has in the queue still sets
            # the ports (their other drivers keep driving them)
            src_port.remove_wires()

        # The inputs, and the inout ports (which are outputs too)
        for dst_port in self._ports:
            for driver in dst_port.get_drivers():
                driver.disconnect(dst_port)

    def add_event(
        self, port: PortOutDelta | PortMultiBitWire | PortInOut, value: VALUE_TYPE, delay_ns: int
    ) -> None:
        """Add delta cycle event"""
        self._circuit.add_event(port, value, delay_ns)

    def __str__(self) -> str:
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

    def onpress(self) -> None:
        """What to happen for an interactive activation"""

    def onrelease(self) -> None:
        """What to happen for an interactive de-activation"""

    def settings_to_dict(self) -> dict[str, ParameterValue]:
        """Return component settings as a dict"""
        return copy.deepcopy(self._parameters)

    @classmethod
    def get_parameters(cls) -> dict[str, Parameter]:
        """Return parameters"""
        return {}

    @classmethod
    def get_circuit_parameters(cls, circuit: Circuit) -> dict[str, Parameter]:
        """
        Return parameters for a new component in 'circuit',
        for components whose parameters depend on the other components (like label wires)
        """
        return cls.get_parameters()

    def update_settings(self, settings: dict[str, ParameterValue]) -> None:
        """Update parameters from settings dict"""
        for setting, value in settings.items():
            self.parameter_set(setting, value)
        # Once, with all the new settings
        self.reconfigure()

    def reconfigure(self) -> None:
        """Update the component from the parameters"""

    def get_reconfigurable_parameters(self) -> dict[str, Parameter]:
        """Return reconfigurable parameters"""
        reconfigurable_parameters: dict[str, Parameter] = {}
        for parameter, parameter_dict in self.get_parameters().items():
            if parameter_dict.get("reconfigurable", False):
                reconfigurable_parameters[parameter] = copy.deepcopy(parameter_dict)
                reconfigurable_parameters[parameter]["default"] = self.parameter_get(parameter)
                if reconfigurable_parameters[parameter]["type"] == "width_pow2":
                    reconfigurable_parameters[parameter]["type"] = "int"
                    reconfigurable_parameters[parameter]["min"] = 0
                    reconfigurable_parameters[parameter]["max"] = (
                        2 ** self.parameter_get("width") - 1
                    )
        return reconfigurable_parameters


class MultiComponent(Component):
    """
    A component that holds one or several sub components.
    The sub components are in the circuit too, so the circuit initializes them.
    """

    def __init__(self, circuit: Circuit, name: str | None = None) -> None:
        super().__init__(circuit, name)
        self._components: list[Component] = []

    def remove_all_components(self) -> None:
        """Remove all sub components, from this component and from the circuit"""
        for component in self._components:
            self.circuit.delete_component(component)
        self._components = []

    def add(self, component: Component) -> None:
        """Add sub-component to MultiComponent"""
        self._components.append(component)
        component.parent = self


class CallbackComponent(Component):
    """
    A component that will call a callback function upon change,
    this is used to for example output text in stdout or update GUI
    objects when the component change value.
    """

    def __init__(
        self,
        circuit: Circuit,
        name: str | None,
        callback: Callable[[Component], None] | None = None,
    ) -> None:
        super().__init__(circuit, name)
        self._callback = callback

    def set_callback(self, callback: Callable[[Component], None]) -> None:
        """Set CallbackComponent callback function"""
        self._callback = callback

    def update(self) -> None:
        """Call CallbackComponent callback function if available"""
        if self._callback is not None:
            self._callback(self)
