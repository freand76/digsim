# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""
Module with classes to parse a yosys netlist.
Only the parts of the netlist that are used to build a component are read, pydantic
ignores the rest (for example net names, attributes and cell parameters).
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field
from pydantic.dataclasses import dataclass


NET_TYPE = Literal["X", "x", "0", "1"] | int
BIT_TYPE = list[NET_TYPE]


@dataclass
class NetPort:
    parent: YosysModule | YosysCell
    parent_name: str
    name: str
    bit_index: int | None = None


@dataclass
class Nets:
    source: dict[NET_TYPE, NetPort] = Field(default_factory=dict)
    sinks: dict[NET_TYPE, list[NetPort]] = Field(default_factory=dict)


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

    def get_nets(self, name: str, nets: Nets) -> None:
        for port_name, net_list in self.connections.items():
            if not net_list:
                # Handle empty net_list, e.g., by skipping or raising an error
                continue
            net = net_list[0]
            port = NetPort(parent=self, parent_name=name, name=port_name)
            if self.port_directions[port_name] == "input":
                if net not in nets.sinks:
                    nets.sinks[net] = []
                nets.sinks[net].append(port)
            else:
                nets.source[net] = port

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
        nets = Nets()

        for port_name, port_item in self.ports.items():
            for bit_index, net in enumerate(port_item.bits):
                port = NetPort(parent=self, parent_name="top", name=port_name, bit_index=bit_index)
                if port_item.is_output:
                    if net not in nets.sinks:
                        nets.sinks[net] = []
                    nets.sinks[net].append(port)
                else:
                    nets.source[net] = port

        for cell_name, cell in self.cells.items():
            cell.get_nets(cell_name, nets)

        return nets


@dataclass
class YosysNetlist:
    modules: dict[str, YosysModule] = Field(default_factory=dict)

    def get_modules(self) -> dict[str, YosysModule]:
        return self.modules
