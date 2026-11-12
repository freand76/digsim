# Copyright (c) Fredrik Andersson, 2023-2026
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


# The layout of a circuit file: the indent of each level, and the width of its lines
JSON_INDENT = 4
JSON_WIDTH = 99


def json_text(value: Any, level: int = 0, used: int = 0) -> str:
    """
    The JSON text of a value, compact: a list or an object that fits on a line is on one
    line, and the short items of a long list fill the lines. Otherwise indented like
    json.dumps(indent=4). 'used' is the length of the line before the value.
    """
    line = json.dumps(value)
    # Room for a comma after the value
    if not isinstance(value, dict | list) or used + len(line) + 1 <= JSON_WIDTH:
        return line
    inner = " " * (JSON_INDENT * (level + 1))
    end = " " * (JSON_INDENT * level)
    if isinstance(value, dict):
        items = []
        for key, item in value.items():
            start = f"{inner}{json.dumps(key)}: "
            items.append(start + json_text(item, level + 1, len(start)))
        return "{\n" + ",\n".join(items) + "\n" + end + "}"
    texts = [json.dumps(item) for item in value]
    if all(len(inner) + len(text) + 1 <= JSON_WIDTH for text in texts) and not any(
        isinstance(item, dict) for item in value
    ):
        # Short items, as many on a line as fit
        lines = [inner]
        for text in texts:
            if lines[-1] != inner and len(lines[-1]) + len(text) + 2 > JSON_WIDTH:
                lines[-1] = lines[-1].rstrip()
                lines.append(inner)
            lines[-1] += text + ", "
        lines[-1] = lines[-1][:-2]
        return "[\n" + ",\n".join(line.rstrip(",") for line in lines) + "\n" + end + "]"
    items = [inner + json_text(item, level + 1, len(inner)) for item in value]
    return "[\n" + ",\n".join(items) + "\n" + end + "]"


def write_json_file(filename: str | Path, data: Any) -> None:
    """Write a data class (or a dict of it) to a circuit file"""
    text = json_text(data if isinstance(data, dict) else asdict(data))
    with open(filename, mode="w", encoding="utf-8") as json_file:
        json_file.write(text + "\n")


def find_port(circuit: Circuit, name: str) -> Port:
    """A port by its name, "component.port" """
    # The component name can contain dots but a port name can't
    component_name, _, port_name = name.rpartition(".")
    return circuit.get_component(component_name).port(port_name)


@dataclass
class LineDataClass:
    """
    A line of wires in the GUI, where each output port drives each input port: its ports
    ("component.port"), the points where its segments turn or meet ({id: [x, y]}), and its
    horizontal and vertical segments, each between two ports or points.
    """

    ports: list[str]
    points: dict[str, list[int]] = Field(default_factory=dict)
    segments: list[list[str]] = Field(default_factory=list)

    @staticmethod
    def width(ports: list[Port]) -> int | None:
        """
        The width of a line with these ports: the width of most of them, of the first
        one where there are as many of two widths. A port of another width is not on it.
        """
        widths = [port.width for port in ports]
        return max(widths, key=widths.count) if widths else None

    def connect(self, circuit: Circuit, errors: list[str] | None = None) -> None:
        """
        Connect each output port of the line to each of its input ports. With 'errors',
        a port that isn't there or a pair that can't be connected is added to it, and the
        others are connected, else the first error is raised.
        """
        from digsim.circuit.components.atoms import DigsimException, PortConnectionError

        def failed(exc: DigsimException) -> None:
            if errors is None:
                raise exc
            errors.append(f"{exc.__class__.__name__}:{exc!s}")

        ports: list[Port] = []
        for name in self.ports:
            try:
                ports.append(find_port(circuit, name))
            except DigsimException as exc:
                failed(exc)
        width = LineDataClass.width(ports)
        for port in [port for port in ports if port.width != width]:
            failed(
                PortConnectionError(
                    f"{port.path()}.{port.name()} has width {port.width}, its line {width}"
                )
            )
        ports = [port for port in ports if port.width == width]
        for src_port in ports:
            if not src_port.is_output():
                continue
            for dst_port in ports:
                # An inout port is both, it drives the others
                if (
                    dst_port.is_input()
                    and dst_port is not src_port
                    and dst_port not in src_port.wired_ports
                ):
                    try:
                        src_port.wire = dst_port
                    except DigsimException as exc:
                        failed(exc)


@dataclass
class WireDataClass:
    src: str
    dst: str

    def connect(self, circuit: Circuit) -> None:
        find_port(circuit, self.src).wire = find_port(circuit, self.dst)

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
    """A circuit file. A GUI circuit file has lines (see LineDataClass) for its wires."""

    circuit: CircuitDataClass
    lines: list[LineDataClass] = Field(default_factory=list)

    @staticmethod
    def load(filename: str | Path) -> CircuitFileDataClass:
        return CircuitFileDataClass(**read_json_file(filename))

    def save(self, filename: str | Path) -> None:
        data = asdict(self)
        if not self.lines:
            del data["lines"]
        write_json_file(filename, data)
