# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""
Module that handles the dataclasses for circuit load/save
"""

from __future__ import annotations

import importlib
import json
from dataclasses import asdict

from pydantic import Field
from pydantic.dataclasses import dataclass


@dataclass
class WireDataClass:
    src: str
    dst: str

    def connect(self, circuit):
        src_comp_name, src_port_name = self.src.split(".")
        dst_comp_name, dst_port_name = self.dst.split(".")
        src_comp = circuit.get_component(src_comp_name)
        dst_comp = circuit.get_component(dst_comp_name)
        src_comp.port(src_port_name).wire = dst_comp.port(dst_port_name)

    @classmethod
    def list_from_port(cls, src_port):
        wires = []
        for port in src_port.wired_ports:
            # Only add port on top-level components
            if port.parent().is_toplevel():
                wires.append(
                    WireDataClass(
                        src=f"{src_port.parent().name()}.{src_port.name()}",
                        dst=f"{port.parent().name()}.{port.name()}",
                    )
                )
        return wires


@dataclass
class ComponentDataClass:
    """Component data class"""

    name: str
    type: str
    display_name: str = Field(default="")
    settings: dict = Field(default_factory=dict)

    def create(self, circuit):
        """Factory: Create a component from a dict"""
        if "path" in self.settings:
            self.settings["path"] = circuit.load_path(self.settings["path"])

        py_module_name = ".".join(self.type.split(".")[0:-1])
        py_class_name = self.type.split(".")[-1]

        module = importlib.import_module(py_module_name)
        class_ = getattr(module, py_class_name)
        component = class_(circuit=circuit, **self.settings)
        component.set_name(self.name)
        if self.display_name is not None:
            component.set_display_name(self.display_name)
        return component

    @staticmethod
    def from_component(component):
        """Return the component information as a dict, used when storing a circuit"""
        module_split = type(component).__module__.split(".")
        type_str = ""
        for module in module_split:
            if not module.startswith("_"):
                type_str += f"{module}."
        type_str += type(component).__name__

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
    def from_circuit(circuit):
        dc = CircuitDataClass(name=circuit.name)
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
    def load(filename):
        try:
            with open(filename, mode="r", encoding="utf-8") as json_file:
                dc = CircuitFileDataClass(**json.load(json_file))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Malformed JSON file: {filename} - {exc}") from exc
        except FileNotFoundError as exc:
            raise FileNotFoundError(f"File not found: {filename}") from exc
        return dc

    def save(self, filename):
        json_object = json.dumps(asdict(self), indent=4)
        with open(filename, mode="w", encoding="utf-8") as json_file:
            json_file.write(json_object)
