# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""
The settings of a component in the settings pane: its parameters with their values, and
the settings of a new component (kept free from Qt imports so that it can be tested
without a display)
"""

from __future__ import annotations

import copy
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from digsim.circuit.components import FlipFlop, SubCircuit, YosysComponent
from digsim.circuit.components.atoms import Component, ComponentException, Parameter


if TYPE_CHECKING:
    from digsim.circuit import Circuit


# The parameter that chooses the kind of flip-flop, the class of the component
CLASS_PARAMETER = "name"

# The name of the component, in the pane but not a setting of the component
NAME_PARAMETER = "_name"

# A name is a part of the name of a port ("component.port") and of a VCD signal
NAME_PATTERN = r"[^\s.]+"

# The parameters that are chosen before a component is added, they have no default
CHOSEN_FIRST = ("path", "ic_name")


def _flip_flop_classes() -> dict[str, str]:
    return FlipFlop.get_parameters()[CLASS_PARAMETER]["component_list"]


def is_flip_flop(component: Component) -> bool:
    """A flip-flop, one of the kinds that the FlipFlop of the GUI chooses between"""
    return type(component).__name__ in _flip_flop_classes()


def given_name(component: Component) -> str:
    """
    The name a component gets when it is made, before a suffix that makes it unique: the
    module of a Verilog component or IC, the file of a subcircuit, else the class
    """
    if isinstance(component, YosysComponent) and component.module_name():
        return component.module_name()
    if isinstance(component, SubCircuit):
        return Path(str(component.settings_to_dict()["path"])).stem
    return type(component).__name__


def has_given_name(component: Component) -> bool:
    """The component has the name it got, like ttl_7485_1, not one the user gave it"""
    return (
        re.fullmatch(rf"{re.escape(given_name(component))}(_\d+)?", component.name()) is not None
    )


def name_problem(name: str, component: Component, circuit: Circuit) -> str:
    """Why a component can't have a name (empty if it can): like the pane's Name says"""
    if re.fullmatch(NAME_PATTERN, name) is None:
        return "a name can't be empty or have spaces or dots"
    for other in circuit.get_toplevel_components():
        if other is not component and other.name() == name:
            return f"{name} is the name of another component"
    return ""


def unique_name(name: str, taken: set[str]) -> str:
    """The name, with a suffix like _1 if it is taken"""
    unique, number = name, 1
    while unique in taken:
        unique, number = f"{name}_{number}", number + 1
    return unique


def pane_parameters(component: Component, circuit: Circuit) -> dict[str, Parameter]:
    """
    The parameters of a component, each with its value as the default: the settings that
    the settings pane shows. The name of the component is first, and a flip-flop has the
    kind of flip-flop too.
    """
    values = component.settings_to_dict()
    parameters: dict[str, Parameter] = {
        NAME_PARAMETER: {
            "type": "str",
            "description": "Name",
            "default": component.name(),
            "single_line": True,
            "invalid_list": [
                other.name()
                for other in circuit.get_toplevel_components()
                if other is not component
            ],
            "pattern": NAME_PATTERN,
        }
    }
    if is_flip_flop(component):
        parameter = copy.deepcopy(FlipFlop.get_parameters()[CLASS_PARAMETER])
        parameter["default"] = type(component).__name__
        parameters[CLASS_PARAMETER] = parameter
    reconfigurable = component.get_reconfigurable_parameters()
    for name, parameter in type(component).get_circuit_parameters(circuit).items():
        if parameter.get("reconfigurable", False) and name not in reconfigurable:
            # Not for this component, like synthesis options for a netlist file
            continue
        parameter = copy.deepcopy(parameter)
        if name in values:
            parameter["default"] = values[name]
        if "invalid_list" in parameter:
            # Its own value is not taken
            parameter["invalid_list"] = [
                value for value in parameter["invalid_list"] if value != values.get(name)
            ]
        if parameter["type"] == "intrange" and parameter.get("default") in parameter["range"]:
            parameter["default_index"] = parameter["range"].index(parameter["default"])
        if (
            parameter["type"] == "list"
            and name in values
            and values[name] not in parameter["items"]
        ):
            # Like the label of a wire source whose sink is gone
            parameter["items"] = [str(values[name]), *parameter["items"]]
        parameters[name] = parameter
    return parameters


def pane_values(parameters: dict[str, Parameter]) -> dict[str, Any]:
    """The values of the parameters of pane_parameters()"""
    return {name: parameter.get("default") for name, parameter in parameters.items()}


def changes(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    """The settings that are different"""
    return {name: value for name, value in after.items() if before.get(name) != value}


def new_settings(parameters: dict[str, Parameter], chosen: dict[str, Any]) -> dict[str, Any]:
    """
    The settings of a new component: the 'chosen' ones (see CHOSEN_FIRST), and the
    defaults of the others, which the settings pane can change after it is added. A text
    that must be unique, like a label, gets an x until it is. Raises ComponentException
    when there is nothing to choose from, like a wire source without a wire sink.
    """
    settings = dict(chosen)
    for name, parameter in parameters.items():
        if name in settings:
            continue
        kind = parameter["type"]
        if kind == "component_name":
            settings[name] = next(iter(parameter["component_list"]))
        elif kind == "list" and "default" not in parameter:
            if not parameter["items"]:
                raise ComponentException(f"No {parameter['description'].lower()} to choose from")
            settings[name] = parameter["items"][0]
        elif kind == "intrange" and "default" not in parameter:
            settings[name] = parameter["range"][parameter["default_index"]]
        elif "default" in parameter:
            value = copy.deepcopy(parameter["default"])
            while isinstance(value, str) and value in parameter.get("invalid_list", []):
                value += "x"
            settings[name] = value
    return settings
