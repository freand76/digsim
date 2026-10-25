# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""
The ports of a Yosys component that change when its Verilog changes, and the wires that
go with them. No Qt, so that it can be tested.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from digsim.circuit import Circuit
from digsim.circuit.components import YosysComponent, YosysVariant
from digsim.circuit.components._yosys_component import (
    YosysComponentException,
    parameter_dict,
    parameter_text,
)
from digsim.storage_model import LineDataClass
from digsim.utils import YosysNetlist


# Port name to (is output, width)
Interface = dict[str, tuple[bool, int]]


@dataclass
class InterfaceChanges:
    """How the ports of a module change"""

    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    # Port name to (old width, new width)
    width: dict[str, tuple[int, int]] = field(default_factory=dict)
    # Ports that change from input to output or back
    direction: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return bool(self.added or self.removed or self.width or self.direction)

    def gone(self) -> set[str]:
        """The ports whose wires are removed: the removed ports and the changed ones"""
        return {*self.removed, *self.width, *self.direction}

    def describe(self) -> list[str]:
        """A line for each change"""
        lines = [f"Port '{name}' is removed" for name in self.removed]
        lines += [
            f"Port '{name}' has {new} bits instead of {old}"
            for name, (old, new) in self.width.items()
        ]
        lines += [f"Port '{name}' changes direction" for name in self.direction]
        lines += [f"Port '{name}' is new" for name in self.added]
        return lines


def interface_changes(old: Interface, new: Interface) -> InterfaceChanges:
    """The changes from the old ports to the new, in the order of the ports"""
    changes = InterfaceChanges()
    for name, (is_output, width) in old.items():
        if name not in new:
            changes.removed.append(name)
            continue
        new_output, new_width = new[name]
        if new_output != is_output:
            changes.direction.append(name)
        elif new_width != width:
            changes.width[name] = (width, new_width)
    changes.added = [name for name in new if name not in old]
    return changes


def removed_wires(
    lines: list[LineDataClass], component_names: list[str], changes: InterfaceChanges
) -> list[str]:
    """The ports of the components on lines (like "counter.y") whose wires are removed"""
    gone = {f"{component}.{port}" for component in component_names for port in changes.gone()}
    return sorted({name for line in lines for name in line.ports if name in gone})


def same_file(first: str | Path, second: str | Path) -> bool:
    """True if two paths are the same file"""
    return Path(first).resolve() == Path(second).resolve()


def components_of_file(circuit: Circuit, path: str | Path) -> list[YosysComponent]:
    """The Yosys components made from a file"""
    return [
        component
        for component in circuit.get_toplevel_components()
        if isinstance(component, YosysComponent)
        and component.source_file is not None
        and same_file(component.source_file, path)
    ]


def load_netlists(
    path: str | Path,
    variants: set[YosysVariant],
    log: list[str] | None = None,
    cached: bool = True,
) -> dict[YosysVariant, dict[str, Any]]:
    """
    The netlists of a Verilog file or a netlist file, for the components made from it:
    synthesized into gates or functional blocks, with the parameters of each variant that
    they need. A netlist file is the same for all.

    Raises:
        DigsimException: If the Verilog can't be synthesized or the netlist file is not
            a Yosys netlist (SynthesisException, YosysComponentException).
        OSError: If the file can't be read.
    """
    path = str(path)
    if path.endswith(".json"):
        with open(path, encoding="utf-8") as json_file:
            try:
                netlist_dict = json.load(json_file)
                modules = YosysNetlist(**netlist_dict).get_modules()
            except (ValueError, TypeError) as exc:
                # Malformed JSON, or JSON that is not a netlist (pydantic ValidationError)
                raise YosysComponentException(f"Not a Yosys netlist: '{path}'") from exc
        if len(modules) != 1:
            raise YosysComponentException(f"Not a Yosys netlist with one module: '{path}'")
        return dict.fromkeys(variants, netlist_dict)
    return {
        variant: YosysComponent.synthesize_file(
            path,
            variant.functional,
            log=log,
            cached=cached,
            parameters=parameter_dict(variant.parameters),
        )
        for variant in sorted(variants)
    }


def variant_with(component: YosysComponent, parameters: str | None) -> YosysVariant:
    """
    The variant of a component with other parameters ("NAME=VALUE,...", None for the
    ones it has)
    """
    if parameters is None:
        return component.variant
    return YosysVariant(component.functional, parameter_text(parameter_dict(parameters)))


def parameter_column(texts: dict[str, str]) -> str:
    """
    The values typed for the parameters of a component, by parameter, as "NAME=VALUE,..."
    (an empty value is the default): integers like 8, -1 or 0xff.

    Raises:
        ValueError: If a value is not an integer: (message, parameter name).
    """
    values: dict[str, int] = {}
    for name, text in texts.items():
        text = text.strip()
        if not text:
            continue
        try:
            values[name] = int(text) if text.lstrip("+-").isdigit() else int(text, 0)
        except ValueError:
            raise ValueError(f"{name} is not an integer: '{text}'", name) from None
    return parameter_text(values)


def change_message(name: str, changes: InterfaceChanges, removed: list[str]) -> str:
    """The text that asks if the ports of a component may change"""
    text = f"The ports of '{name}' change:\n"
    text += "".join(f" - {line}\n" for line in changes.describe())
    if removed:
        text += "\nThe wires to these ports are removed:\n"
        text += "".join(f" - {port}\n" for port in removed)
    text += "\nThis can't be undone."
    return text


@dataclass
class YosysUpdate:
    """
    New netlists for the Yosys components of a file, checked and ready to apply (see
    ModelComponents.prepare_yosys_update)
    """

    path: str
    # Netlist dicts, by how they are synthesized
    netlists: dict[YosysVariant, dict[str, Any]]
    # The components of the file, and how their ports change
    changes: dict[YosysComponent, InterfaceChanges]
    # The ports on wires that are removed with the ports, like "counter.y"
    removed: list[str] = field(default_factory=list)
    # How each component is synthesized now: its new parameters, if they change
    variants: dict[YosysComponent, YosysVariant] = field(default_factory=dict)

    def variant(self, component: YosysComponent) -> YosysVariant:
        """The variant of a component, with its new parameters"""
        return self.variants.get(component, component.variant)

    def ports_change(self) -> bool:
        """True if the ports of a component change"""
        return any(self.changes.values())

    def port_changes(self) -> InterfaceChanges:
        """
        How the ports change (the components of a file have the same ports, unless they
        have different parameters: then the changes of one of them)
        """
        return next((changes for changes in self.changes.values() if changes), InterfaceChanges())

    def names(self) -> str:
        """The names of the components"""
        return ", ".join(component.name() for component in self.changes)
