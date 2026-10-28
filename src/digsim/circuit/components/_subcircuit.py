# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""A subcircuit: another circuit file used as a component, through its circuit ports"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from digsim.storage_model import AppFileDataClass, ComponentDataClass, GuiPositionDataClass

from ._circuit_port import CircuitInOut, CircuitInput, CircuitOutput
from .atoms import (
    VALUE_TYPE,
    Component,
    DigsimException,
    MultiComponent,
    Parameter,
    ParameterValue,
    Port,
    PortIn,
    PortInOut,
    PortOutDelta,
    PortWire,
)


if TYPE_CHECKING:
    from digsim.circuit import Circuit

# The type names of the circuit ports in a circuit file, and their directions
_PORT_TYPES = {
    "digsim.circuit.components.CircuitInput": CircuitInput.DIRECTION,
    "digsim.circuit.components.CircuitOutput": CircuitOutput.DIRECTION,
    "digsim.circuit.components.CircuitInOut": CircuitInOut.DIRECTION,
}

# The files of the subcircuits that are being loaded, to find a file that uses itself
_loading: list[Path] = []


class SubCircuitException(DigsimException):
    """A subcircuit can't be loaded from its file"""


@dataclass
class FilePort:
    """A circuit port of a circuit file: its label, direction and width, and its component"""

    label: str
    direction: str
    width: int
    component: str


def port_order(ports: list[FilePort], gui: dict[str, GuiPositionDataClass]) -> list[FilePort]:
    """
    The order of the ports of a subcircuit: as the circuit ports are in the file, from top
    to bottom (from left to right on the same height), and by label in a file without
    positions (a circuit made in Python). A setting of each circuit port can replace this.
    """

    def key(port: FilePort) -> tuple[int, int, str]:
        position = gui.get(port.component)
        if position is None:
            return (0, 0, port.label)
        return (position.y, position.x, port.label)

    return sorted(ports, key=key)


def read_circuit_file(path: Path) -> AppFileDataClass:
    """A circuit file, a GUI file with lines or a Python one with wires"""
    try:
        return AppFileDataClass.load(path)
    except (OSError, ValueError) as exc:
        # Missing, unreadable or malformed (pydantic's ValidationError is a ValueError)
        raise SubCircuitException(f"Could not read the subcircuit {path}: {exc!s}") from exc


def file_ports(file_dc: AppFileDataClass) -> list[FilePort]:
    """The circuit ports of a circuit file, in the order of port_order()"""
    ports = []
    for component_dc in file_dc.circuit.components:
        direction = _PORT_TYPES.get(component_dc.type)
        if direction is not None:
            settings = component_dc.settings
            ports.append(
                FilePort(
                    label=str(settings.get("label", "")),
                    direction=direction,
                    width=int(settings.get("width", 1)),
                    component=component_dc.name,
                )
            )
    return port_order(ports, file_dc.gui)


def files_used(path: str | Path) -> set[Path]:
    """
    The circuit files that a subcircuit's file uses, through its subcircuits and theirs
    (resolved paths). A file that can't be read uses nothing more.
    """
    found: set[Path] = set()
    todo = [Path(path)]
    while todo:
        current = todo.pop()
        try:
            file_dc = AppFileDataClass.load(current)
        except (OSError, ValueError):
            continue
        for component_dc in file_dc.circuit.components:
            if not component_dc.type.endswith(".SubCircuit"):
                continue
            used = Path(str(component_dc.settings.get("path", "")))
            if not used.is_absolute():
                used = current.parent / used
            key = used.resolve()
            if key not in found:
                found.add(key)
                todo.append(used)
    return found


class _InOutBridge(Component):
    """
    Connects an inout port of a subcircuit, which is driven and read bit by bit, to the
    ports inside it, which drive and read the whole bus: the inner drivers drive 'drive',
    and 'read' drives the inner readers with the value of the wire
    """

    def __init__(self, circuit: Circuit, name: str, inout: PortInOut) -> None:
        super().__init__(circuit, name)
        self.inout = inout
        width = inout.width
        self.drive_in = PortIn(self, "drive", width=width)
        self.add_port(self.drive_in)
        self.read_out = PortOutDelta(self, "read", width=width, delay_ns=0)
        self.read_out.set_tristate()
        self.add_port(self.read_out)
        self._bit_drivers: list[PortOutDelta] = []
        self._bit_readers: list[PortIn] = []
        # What it drives and reads last, set before the wiring updates it
        self._driven: list[VALUE_TYPE] = []
        self._read: VALUE_TYPE = "X"
        for bit_id in range(width):
            driver = PortOutDelta(self, f"drive_{bit_id}", delay_ns=0)
            driver.set_tristate()
            driver.wire = inout.get_drive_bit(bit_id)
            self._bit_drivers.append(driver)
            reader = PortIn(self, f"read_{bit_id}")
            inout.get_bit(bit_id).wire = reader
            self._bit_readers.append(reader)

    def init(self) -> None:
        super().init()
        for port in [*self._bit_drivers, *self._bit_readers]:
            port.init()
        self._driven = []
        self._read = "X"

    def default_state(self) -> None:
        self.update()

    def update(self) -> None:
        # What the inside drives, nothing ("Z") when nothing inside drives
        drive = self.drive_in.value if self.drive_in.has_driver() else "Z"
        bits = [
            (drive >> bit_id) & 1 if isinstance(drive, int) else drive
            for bit_id in range(len(self._bit_drivers))
        ]
        if bits != self._driven:
            self._driven = bits
            for driver, bit in zip(self._bit_drivers, bits, strict=True):
                driver.value = bit
        # The value of the wire, for the inside
        values = [reader.value for reader in self._bit_readers]
        read: VALUE_TYPE
        if all(value == "Z" for value in values):
            read = "Z"
        elif all(isinstance(value, int) for value in values):
            read = sum(int(value) << bit_id for bit_id, value in enumerate(values))
        else:
            read = "X"
        if read != self._read:
            self._read = read
            self.read_out.value = read

    def remove_connections(self) -> None:
        for driver in self._bit_drivers:
            driver.remove_wires()
        for reader in self._bit_readers:
            for source in reader.get_drivers():
                source.disconnect(reader)
        super().remove_connections()


class SubCircuit(MultiComponent):
    """
    Another circuit file used as a component. Its ports are the circuit ports of the file
    (CircuitInput, CircuitOutput and CircuitInOut): an input, an output or an inout port
    for each, named and as wide as it, in the order of the circuit ports in the file from
    top to bottom. The components of the file are parts of the subcircuit (a VCD file
    names them "subcircuit.component"), connected like in the file, with the ports of the
    subcircuit where the circuit ports were. A subcircuit in the file is loaded the same
    way, its file relative to that file.

    Ports:
        <label>: An input, an output or an inout port for each circuit port of the file.

    Args:
        circuit: The circuit to add the component to.
        path: The circuit file.
        name: The component name, the name of the file without .circuit if not given.
    """

    def __init__(self, circuit: Circuit, path: str | Path, name: str | None = None) -> None:
        self._path = Path(path)
        super().__init__(circuit, name or self._path.stem)
        self.set_display_name(self._path.stem)
        self._bridges: list[_InOutBridge] = []
        # The parts by their names in the file, and the file they were built from
        self._parts: dict[str, Component] = {}
        file_dc = self._read_file()
        self._file_dc = file_dc
        self._interface: list[FilePort] = file_ports(file_dc)
        self._outer: dict[str, Port] = {}
        for file_port in self._interface:
            port: Port
            if file_port.direction == CircuitInOut.DIRECTION:
                port = PortInOut(self, file_port.label, width=file_port.width)
                port.set_tristate()
            else:
                output = file_port.direction == CircuitOutput.DIRECTION
                port = PortWire(self, file_port.label, width=file_port.width, output=output)
            self._outer[file_port.label] = port
            self.add_port(port)
        self.parameter_set("path", str(path))
        self._build(file_dc)

    def source_file(self) -> Path:
        """The circuit file"""
        return self._path

    def _read_file(self) -> AppFileDataClass:
        """The circuit file, an error if it is loaded already (it would use itself)"""
        key = self._path.resolve()
        if key in _loading:
            chain = " -> ".join(path.name for path in [*_loading, key])
            raise SubCircuitException(f"The subcircuit uses itself: {chain}")
        return read_circuit_file(self._path)

    def layout(self) -> AppFileDataClass:
        """The circuit file as it was when the parts were built: positions and lines"""
        return self._file_dc

    def has_layout(self) -> bool:
        """Is it from a GUI file, with positions and lines (not a circuit made in Python)"""
        return bool(self._file_dc.gui) and bool(self._file_dc.lines)

    def parts(self) -> list[Component]:
        """The parts, the components of the file (and the bridges of the inout ports)"""
        return list(self._components)

    def part(self, name: str) -> Component | None:
        """A part by its name in the file, it can have another name in the circuit"""
        return self._parts.get(name)

    def file_ports(self) -> list[FilePort]:
        """The circuit ports of the file, in the order of the ports"""
        return list(self._interface)

    def outer_port(self, label: str) -> Port:
        """The port of the subcircuit for a circuit port of the file"""
        return self._outer[label]

    def interface(self) -> dict[str, tuple[str, int]]:
        """The ports, label: (direction, width)"""
        return {port.label: (port.direction, port.width) for port in self._interface}

    @staticmethod
    def file_interface(path: str | Path) -> dict[str, tuple[str, int]]:
        """The ports of a subcircuit of a file, label: (direction, width)"""
        ports = file_ports(read_circuit_file(Path(path)))
        return {port.label: (port.direction, port.width) for port in ports}

    def _build(self, file_dc: AppFileDataClass) -> None:
        """Create the components of the file as parts, and connect them"""
        key = self._path.resolve()
        _loading.append(key)
        try:
            names = self._create_parts(file_dc)
        finally:
            _loading.pop()
        self._parts = names
        self._file_dc = file_dc
        self._connect(file_dc, names)
        # An output driven only by tristate parts is a tristate output (it can share a wire)
        for port in self._outer.values():
            if port.is_output() and not port.is_inout():
                drivers = port.get_drivers()
                port.set_tristate(bool(drivers) and all(d.is_tristate() for d in drivers))

    def _create_parts(self, file_dc: AppFileDataClass) -> dict[str, Component]:
        """The parts, by their names in the file (they can get other names in the circuit)"""
        folder = self._path.parent
        ports = {port.component for port in self._interface}
        names: dict[str, Component] = {}
        for component_dc in file_dc.circuit.components:
            if component_dc.name in ports:
                continue
            settings = dict(component_dc.settings)
            if settings.get("path") and not os.path.isabs(str(settings["path"])):
                # A file of the part, relative to the subcircuit's file. Absolute, or the
                # circuit would load it relative to its own folder.
                settings["path"] = os.path.abspath(folder / str(settings["path"]))
            part_dc = ComponentDataClass(
                name=component_dc.name,
                type=component_dc.type,
                display_name=component_dc.display_name,
                settings=settings,
            )
            try:
                part = part_dc.create(self.circuit)
            except DigsimException as exc:
                raise SubCircuitException(
                    f"Could not create {component_dc.name} of the subcircuit {self._path}: {exc!s}"
                ) from exc
            self.add(part)
            names[component_dc.name] = part
        return names

    def _port(self, key: str, names: dict[str, Component]) -> list[Port]:
        """
        The ports of the subcircuit for a port of the file ("component.port"): the port of a
        part, or for a circuit port the port of the subcircuit (an inout port: the bridge's
        two ports)
        """
        component_name, _, port_name = key.rpartition(".")
        for file_port in self._interface:
            if file_port.component == component_name:
                outer = self._outer[file_port.label]
                if isinstance(outer, PortInOut):
                    bridge = self._bridge(outer)
                    return [bridge.read_out, bridge.drive_in]
                return [outer]
        part = names.get(component_name)
        if part is None:
            raise SubCircuitException(f"The subcircuit {self._path} has no {key}")
        return [part.port(port_name)]

    def _bridge(self, inout: PortInOut) -> _InOutBridge:
        """The bridge of an inout port of the subcircuit, one for each"""
        for bridge in self._bridges:
            if bridge.inout is inout:
                return bridge
        bridge = _InOutBridge(self.circuit, f"{self.name()}_{inout.name()}", inout)
        self.add(bridge)
        self._bridges.append(bridge)
        return bridge

    def _drives(self, port: Port) -> bool:
        """
        Does a port drive the line inside: the outputs of the parts (also of a subcircuit
        part), inout ports, and the inputs of this subcircuit
        """
        if port.parent() is self:
            return not port.is_output()
        return port.is_output()

    def _reads(self, port: Port) -> bool:
        """Is a port driven by the line inside: the inputs of the parts, inout ports, and
        the outputs of this subcircuit"""
        if port.parent() is self:
            return port.is_output()
        return port.is_input()

    def _connect(self, file_dc: AppFileDataClass, names: dict[str, Component]) -> None:
        """Connect the parts like the lines (or the wires) of the file connect them"""
        if file_dc.lines:
            groups = [
                [port for key in line.ports for port in self._port(key, names)]
                for line in file_dc.lines
            ]
        else:
            groups = [
                [*self._port(wire.src, names), *self._port(wire.dst, names)]
                for wire in file_dc.circuit.wires
            ]
        for ports in groups:
            drivers = [port for port in ports if self._drives(port)]
            readers = [port for port in ports if self._reads(port)]
            for driver in drivers:
                for reader in readers:
                    if reader is driver or reader in driver.wired_ports:
                        continue
                    if isinstance(driver.parent(), _InOutBridge) and (
                        driver.parent() is reader.parent()
                    ):
                        # What the bridge reads on the wire is not what the inside drives
                        continue
                    if driver.width != reader.width:
                        raise SubCircuitException(
                            f"The subcircuit {self._path} connects ports of different "
                            f"widths: {driver.name()} and {reader.name()}"
                        )
                    driver.wire = reader

    def reload(self) -> None:
        """
        Build the parts again from the file, which can have changed. Its circuit ports
        must be the same (see interface()).

        Raises:
            SubCircuitException: If the file can't be read, or its ports changed.
        """
        file_dc = self._read_file()
        if file_ports(file_dc) != self._interface:
            raise SubCircuitException(f"The ports of the subcircuit {self._path} changed")
        self.remove_all_components()
        self._bridges = []
        self._build(file_dc)

    def settings_to_dict(self) -> dict[str, ParameterValue]:
        return {"path": self.circuit.store_path(self._path)}

    @classmethod
    def get_parameters(cls) -> dict[str, Parameter]:
        return {
            "path": {
                "type": "path",
                "fileinfo": "Circuit (*.circuit)",
                "description": "Open the circuit file of the subcircuit",
            },
        }
