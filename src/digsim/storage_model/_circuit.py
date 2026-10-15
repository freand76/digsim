# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""
Module that handles the dataclasses for circuit load/save
"""

from __future__ import annotations

import importlib
import json
from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import Field
from pydantic.dataclasses import dataclass


if TYPE_CHECKING:
    from digsim.circuit import Circuit
    from digsim.circuit.components.atoms import Component, Port


def read_json_file(filename: str | Path) -> dict[str, Any]:
    """Read a circuit file (JSON object), ValueError if it isn't one"""
    try:
        with open(filename, mode="r", encoding="utf-8") as json_file:
            file_dict = json.load(json_file)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Malformed JSON file: {filename} - {exc}") from exc
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"File not found: {filename}") from exc
    if not isinstance(file_dict, dict):
        # A ValueError like other malformed files, the callers report those
        raise ValueError(f"Malformed circuit file: {filename} - not a JSON object")  # noqa: TRY004
    return file_dict


def write_json_file(filename: str | Path, data: Any) -> None:
    """Write a data class to a circuit file"""
    json_object = json.dumps(asdict(data), indent=4)
    with open(filename, mode="w", encoding="utf-8") as json_file:
        json_file.write(json_object)


@dataclass
class WireDataClass:
    src: str
    dst: str

    def connect(self, circuit: Circuit) -> None:
        # "component.port", the component name can contain dots but a port name can't
        src_comp_name, _, src_port_name = self.src.rpartition(".")
        dst_comp_name, _, dst_port_name = self.dst.rpartition(".")
        src_comp = circuit.get_component(src_comp_name)
        dst_comp = circuit.get_component(dst_comp_name)
        src_comp.port(src_port_name).wire = dst_comp.port(dst_port_name)

    @classmethod
    def list_from_port(cls, src_port: Port) -> list[WireDataClass]:
        # Only wires between top-level components, the parts of a component are not saved
        return [
            WireDataClass(
                src=f"{src_port.parent().name()}.{src_port.name()}",
                dst=f"{port.parent().name()}.{port.name()}",
            )
            for port in src_port.wired_ports
            if port.parent().is_toplevel()
        ]


@dataclass
class ComponentDataClass:
    """Component data class"""

    name: str
    type: str
    display_name: str = Field(default="")
    settings: dict[str, Any] = Field(default_factory=dict)

    def create(self, circuit: Circuit) -> Component:
        """Factory: Create a component from a dict"""
        settings = dict(self.settings)
        if "path" in settings:
            settings["path"] = circuit.load_path(settings["path"])

        # Imported here: digsim.circuit imports this module
        from digsim.circuit.components.atoms import Component, DigsimException

        py_module_name, _, py_class_name = self.type.rpartition(".")
        try:
            class_ = getattr(importlib.import_module(py_module_name), py_class_name)
        except (ImportError, AttributeError, ValueError) as exc:
            # For example a component from a newer version of DigSim
            raise DigsimException(f"Unknown component type '{self.type}'") from exc
        if not (isinstance(class_, type) and issubclass(class_, Component)):
            raise DigsimException(f"'{self.type}' is not a component")
        try:
            component = class_(circuit=circuit, **settings)
        except TypeError as exc:
            # A setting that the component does not have
            raise DigsimException(f"Invalid settings for '{self.name}': {exc}") from exc
        component.set_name(self.name)
        # Files from older versions have no display name, keep the component's own
        if self.display_name:
            component.set_display_name(self.display_name)
        return component

    @staticmethod
    def from_component(component: Component) -> ComponentDataClass:
        """Return the component information as a dict, used when storing a circuit"""
        # The public module path, without private modules like '_gates'
        modules = [m for m in type(component).__module__.split(".") if not m.startswith("_")]
        type_str = ".".join([*modules, type(component).__name__])

        return ComponentDataClass(
            name=component.name(),
            display_name=component.display_name(),
            type=type_str,
            settings=component.settings_to_dict(),
        )


@dataclass
class CircuitDataClass:
    name: str = "unnamed"
    components: list[ComponentDataClass] = Field(default_factory=list)
    wires: list[WireDataClass] = Field(default_factory=list)

    @staticmethod
    def from_circuit(circuit: Circuit) -> CircuitDataClass:
        dc = CircuitDataClass(name=circuit.name or "unnamed")
        toplevel_components = circuit.get_toplevel_components()
        for comp in toplevel_components:
            dc.components.append(ComponentDataClass.from_component(comp))

        for comp in toplevel_components:
            for port in comp.ports:
                dc.wires.extend(WireDataClass.list_from_port(port))

        return dc


@dataclass
class CircuitFileDataClass:
    circuit: CircuitDataClass

    @staticmethod
    def load(filename: str | Path) -> CircuitFileDataClass:
        return CircuitFileDataClass(**read_json_file(filename))

    def save(self, filename: str | Path) -> None:
        write_json_file(filename, self)
