# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""
Module with classes to parse a yosys netlist.
Only the parts of the netlist that are used to build a component are read, pydantic
ignores the rest (for example net names, attributes and cell parameters).
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
    """A port on a net: a port of the cell 'cell', or bit 'bit_index' of a module port"""

    name: str
    cell: str | None = None
    bit_index: int | None = None


@dataclasses.dataclass
class Nets:
    """The port that drives each net, and the ports that each net drives"""

    source: dict[NET_TYPE, NetPort] = dataclasses.field(default_factory=dict)
    sinks: dict[NET_TYPE, list[NetPort]] = dataclasses.field(default_factory=dict)


@dataclass
class YosysPort:
    direction: str
    bits: BIT_TYPE

    @property
    def is_output(self) -> bool:
        return self.direction == "output"

    def is_same(self, compare_port: YosysPort) -> bool:
        return (compare_port.direction == self.direction) and (
            len(compare_port.bits) == len(self.bits)
        )


@dataclass
class YosysCell:
    type: str
    port_directions: dict[str, str] = Field(default_factory=dict)
    connections: dict[str, BIT_TYPE] = Field(default_factory=dict)

    def component_name(self, name: str) -> str:
        """Return a friendly name for a netlist cell"""
        return f"{name.split('$')[-1]}_{self.component_type()}"

    def component_type(self) -> str:
        """Return a friendly type for a netlist cell"""
        return f"_{self.type[2:-1]}_"


@dataclass
class YosysModule:
    ports: dict[str, YosysPort] = Field(default_factory=dict)
    cells: dict[str, YosysCell] = Field(default_factory=dict)

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
        outputs and cell inputs are driven by them. The cells have single-bit ports.
        """
        nets = Nets()
        for port_name, port in self.ports.items():
            for bit_index, net in enumerate(port.bits):
                net_port = NetPort(port_name, bit_index=bit_index)
                if port.is_output:
                    nets.sinks.setdefault(net, []).append(net_port)
                else:
                    nets.source[net] = net_port
        for cell_name, cell in self.cells.items():
            for port_name, bits in cell.connections.items():
                if not bits:
                    continue
                net_port = NetPort(port_name, cell=cell_name)
                if cell.port_directions[port_name] == "input":
                    nets.sinks.setdefault(bits[0], []).append(net_port)
                else:
                    nets.source[bits[0]] = net_port
        return nets


@dataclass
class YosysNetlist:
    modules: dict[str, YosysModule] = Field(default_factory=dict)

    def get_modules(self) -> dict[str, YosysModule]:
        return self.modules
