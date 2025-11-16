# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""
Module with classes to parse a yosys netlist
"""

from __future__ import annotations

from typing import Any, Literal, Optional, Union

from pydantic import Field
from pydantic.dataclasses import dataclass


BIT_TYPE = list[Union[int, Literal["X"], Literal["x"], Literal["0"], Literal["1"]]]


@dataclass
class NetPort:
    parent: Union[YosysModule, YosysCell]
    parent_name: str
    name: str
    bit_index: Optional[int] = None


@dataclass
class Nets:
    source: dict[int, NetPort] = Field(default_factory=dict)
    sinks: dict[int, list[NetPort]] = Field(default_factory=dict)


@dataclass
class YosysPort:
    direction: str
    bits: BIT_TYPE

    @property
    def is_output(self):
        return self.direction == "output"

    def is_same(self, compare_port):
        return (compare_port.direction == self.direction) and (
            len(compare_port.bits) == len(self.bits)
        )


@dataclass
class YosysCell:
    type: str
    port_directions: dict[str, str] = Field(default_factory=dict)
    connections: dict[str, BIT_TYPE] = Field(default_factory=dict)
    hide_name: int = 0
    parameters: dict[str, Any] = Field(default_factory=dict)
    attributes: dict[str, Any] = Field(default_factory=dict)

    def get_nets(self, name, nets):
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

    def component_name(self, name):
        """Return a friendly name for a netlist cell"""
        return f"{name.split('$')[-1]}_{self.component_type()}"

    def component_type(self):
        """Return a friendly type for a netlist cell"""
        return f"_{self.type[2:-1]}_"


@dataclass
class YosysNetName:
    bits: BIT_TYPE
    attributes: dict[str, Any] = Field(default_factory=dict)
    hide_name: int = 0


@dataclass
class YosysModule:
    attributes: dict[str, Any] = Field(default_factory=dict)
    parameter_default_values: dict[str, Any] = Field(default_factory=dict)
    ports: dict[str, YosysPort] = Field(default_factory=dict)
    cells: dict[str, YosysCell] = Field(default_factory=dict)
    netnames: dict[str, YosysNetName] = Field(default_factory=dict)

    def is_same_interface(self, netlist):
        is_same = True
        if len(netlist.ports) == len(self.ports):
            for netlist_port_name, netlist_port in netlist.ports.items():
                module_port = self.ports.get(netlist_port_name)
                if module_port is None or not module_port.is_same(netlist_port):
                    # Port does not exist or has a different bitwidth
                    is_same = False
                    break
        else:
            # The number of ports does not match
            is_same = False
        return is_same

    def get_nets(self):
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
    creator: Optional[str] = None
    modules: dict[str, YosysModule] = Field(default_factory=dict)

    def get_modules(self):
        return self.modules
