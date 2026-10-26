# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""
Module with classes to parse a yosys netlist.
Only the parts of the netlist that are used to build a component are read, pydantic
ignores the rest (for example net names and attributes).
"""

from __future__ import annotations

import dataclasses
from typing import Literal

from pydantic import Field
from pydantic.dataclasses import dataclass


NET_TYPE = Literal["X", "x", "0", "1"] | int
BIT_TYPE = list[NET_TYPE]


# NetPort and Nets are built from a parsed netlist, not read from JSON: plain dataclasses


@dataclasses.dataclass
class NetPort:
    """
    A port on a net: bit 'bit_index' of a port of the cell 'cell', or of a module port
    (no cell). The gate cells have single-bit ports, the functional cells (like $add)
    have a bit index for each bit of a port.
    """

    name: str
    cell: str | None = None
    bit_index: int | None = None


@dataclasses.dataclass
class Nets:
    """
    The port that drives each net, and the ports that each net drives. The net of a bit of
    an inout module port is driven by the port, with the value of the wire outside, and
    the cell outputs on it are its drivers in 'inout_drivers' instead.
    """

    source: dict[NET_TYPE, NetPort] = dataclasses.field(default_factory=dict)
    sinks: dict[NET_TYPE, list[NetPort]] = dataclasses.field(default_factory=dict)
    inout_drivers: dict[NET_TYPE, list[NetPort]] = dataclasses.field(default_factory=dict)


@dataclass
class YosysPort:
    """
    A port of a module: its direction ("input", "output" or "inout") and the nets of its
    bits
    """

    direction: str
    bits: BIT_TYPE

    @property
    def is_output(self) -> bool:
        return self.direction == "output"

    @property
    def is_inout(self) -> bool:
        return self.direction == "inout"

    def is_same(self, compare_port: YosysPort) -> bool:
        return (compare_port.direction == self.direction) and (
            len(compare_port.bits) == len(self.bits)
        )


@dataclass
class YosysCell:
    """
    A cell of a module, and the nets its ports connect to. A gate cell, like $_AND_, has
    single-bit ports. A functional cell, like $add, has ports of any width, and
    parameters (like the widths) as binary strings.
    """

    type: str
    port_directions: dict[str, str] = Field(default_factory=dict)
    connections: dict[str, BIT_TYPE] = Field(default_factory=dict)
    parameters: dict[str, str | int] = Field(default_factory=dict)

    @property
    def is_gate(self) -> bool:
        """A gate cell, like $_AND_ (not a functional cell like $and)"""
        return self.type.startswith("$_")

    def component_name(self, name: str) -> str:
        """Return a friendly name for a netlist cell"""
        return f"{name.split('$')[-1]}_{self.component_type()}"

    def component_type(self) -> str:
        """Return a friendly type for a netlist cell"""
        if self.is_gate:
            return f"_{self.type[2:-1]}_"
        return self.type[1:]

    def parameter(self, name: str, default: int = 0) -> int:
        """A parameter as a number, bits that are undefined ("x") count as 0"""
        value = self.parameters.get(name)
        if value is None:
            return default
        if isinstance(value, int):
            return value
        if value and all(char in "01xXzZ" for char in value):
            return int("".join("1" if char == "1" else "0" for char in value), 2)
        return default


@dataclass
class YosysNetname:
    """
    A named signal of a module, a wire or register of the Verilog (hierarchical, like
    "ALU.OUT", after flattening), and the nets of its bits. Yosys adds attributes, like the
    names of the values of a SystemVerilog enum ("enum_value_01": "\\RUN").
    """

    bits: BIT_TYPE
    hide_name: int = 0
    attributes: dict[str, str | int] = Field(default_factory=dict)

    def enum_names(self) -> dict[int, str]:
        """The names of the values, for a signal declared as a SystemVerilog enum"""
        names = {}
        for attribute, name in self.attributes.items():
            if attribute.startswith("enum_value_") and isinstance(name, str):
                value = attribute[len("enum_value_") :]
                if value and all(char in "01" for char in value):
                    names[int(value, 2)] = name.lstrip("\\")
        return names


@dataclass
class YosysModule:
    """A module of a netlist: its ports, cells, named signals and parameters"""

    ports: dict[str, YosysPort] = Field(default_factory=dict)
    cells: dict[str, YosysCell] = Field(default_factory=dict)
    netnames: dict[str, YosysNetname] = Field(default_factory=dict)
    # The parameters of the module and their values, as binary strings
    parameter_default_values: dict[str, str | int] = Field(default_factory=dict)

    def signal_names(self) -> list[str]:
        """
        The named signals of the module that are not ports, and not names that Yosys made
        up (hidden names, like "$and$cpu.v:10$5_Y")
        """
        return [
            name
            for name, netname in self.netnames.items()
            if not netname.hide_name
            and not name.startswith("$")
            and name not in self.ports
            and any(isinstance(net, int) for net in netname.bits)
        ]

    def state_names(self, name: str) -> dict[int, str]:
        """
        Names for the values of a signal: the names of a SystemVerilog enum, or else the
        module parameters with the width of the signal (like "parameter IDLE = 2'd0", a
        common way to name states in Verilog). A value with more names gets them all,
        separated by "/".
        """
        netname = self.netnames[name]
        names = netname.enum_names()
        if names:
            return names
        width = len(netname.bits)
        for parameter, value in self.parameter_default_values.items():
            if isinstance(value, str) and len(value) == width and all(c in "01" for c in value):
                number = int(value, 2)
                names[number] = f"{names[number]}/{parameter}" if number in names else parameter
        return names

    def is_same_interface(self, netlist: YosysModule) -> bool:
        """Same port names, with the same directions and bitwidths"""
        if len(netlist.ports) != len(self.ports):
            return False
        return all(
            name in self.ports and self.ports[name].is_same(port)
            for name, port in netlist.ports.items()
        )

    def get_nets(self) -> Nets:
        """
        The nets of the module. Module inputs and cell outputs drive nets, and module
        outputs and cell inputs are driven by them. An inout module port drives its nets
        (constant bits excepted), and the cell outputs on them drive the port.
        """
        nets = Nets()
        inout_nets: set[NET_TYPE] = set()
        for port_name, port in self.ports.items():
            for bit_index, net in enumerate(port.bits):
                net_port = NetPort(port_name, bit_index=bit_index)
                if port.is_output:
                    nets.sinks.setdefault(net, []).append(net_port)
                elif port.is_inout:
                    if isinstance(net, int):
                        nets.source[net] = net_port
                        inout_nets.add(net)
                else:
                    nets.source[net] = net_port
        for cell_name, cell in self.cells.items():
            for port_name, bits in cell.connections.items():
                is_input = cell.port_directions[port_name] == "input"
                for bit_index, net in enumerate(bits):
                    net_port = NetPort(port_name, cell=cell_name, bit_index=bit_index)
                    if is_input:
                        nets.sinks.setdefault(net, []).append(net_port)
                    elif net in inout_nets:
                        nets.inout_drivers.setdefault(net, []).append(net_port)
                    else:
                        nets.source[net] = net_port
        return nets


@dataclass
class YosysNetlist:
    """
    A Yosys JSON netlist, read with YosysNetlist(**netlist_dict). Only the parts that
    DigSim uses are kept.
    """

    modules: dict[str, YosysModule] = Field(default_factory=dict)

    def get_modules(self) -> dict[str, YosysModule]:
        return self.modules
