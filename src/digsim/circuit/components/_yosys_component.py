# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""
Module with classes to create a yosys component
from a yosys json netlist.
"""

import json

import digsim.circuit.components._yosys_atoms
from digsim.synth import Synthesis
from digsim.utils import YosysCell, YosysModule, YosysNetlist

from ._static_level import GND, VDD
from .atoms import Component, DigsimException, MultiComponent, PortMultiBitWire


class YosysComponentException(DigsimException):
    """Yosys component exception class"""


class YosysComponent(MultiComponent):
    """Class to create a yosys component from a yosys json netlist"""

    def __init__(self, circuit, path=None, name=None, nets=True):
        super().__init__(circuit, name)
        self._circuit = circuit
        self._path = str(path)
        self._gates_comp = None
        self._net_comp = None
        self._netlist_module = None
        self._netlist_nets = None
        self._setup_base()

        if nets:
            self._net_comp = Component(self._circuit, "nets")
            self.add(self._net_comp)

        if path is not None:
            self._load_file()

    def _setup_base(self):
        self._gates_comp = MultiComponent(self._circuit, "gates")
        self.add(self._gates_comp)

    def create_from_netlist(self, netlist_object):
        """Create component from netlist object"""
        modules = netlist_object.get_modules()
        module_name = list(modules.keys())[0]
        self._netlist_module = netlist_object.get_modules()[module_name]
        self._netlist_nets = self._netlist_module.get_nets()

        # Set Name
        self.set_name(module_name)
        self.set_display_name(module_name)
        # Add External Ports
        for portname, port_dict in self._netlist_module.ports.items():
            external_port = PortMultiBitWire(
                self, portname, width=len(port_dict.bits), output=port_dict.is_output
            )
            self.add_port(external_port)
        # Create component
        self._create_component()

    def reload_from_netlist(self, netlist_object):
        """Reload netlist from netlist object"""
        modules = netlist_object.get_modules()
        module_name = list(modules.keys())[0]
        reload_module = netlist_object.get_modules()[module_name]
        reload_nets = reload_module.get_nets()

        if not self._netlist_module.is_same_interface(reload_module):
            raise YosysComponentException("Yosys component interface differs")

        # Disconnect ports
        self._disconnect_external_ports()
        # Remove yosys atoms
        self._gates_comp.remove_all_components()
        # Remove nets
        if self._net_comp is not None:
            self._net_comp.delete_all_ports()
        # Setup netlist
        self._netlist_module = reload_module
        self._netlist_nets = reload_nets
        # Create component
        self._create_component()

    def _create_cells(self):
        """Create cells in component"""
        components_dict = {}
        for cellname, cell in self._netlist_module.cells.items():
            if cell.type == "$scopeinfo":
                continue
            component_class = getattr(
                digsim.circuit.components._yosys_atoms, cell.component_type()
            )
            component = component_class(self._circuit, name=cell.component_name(cellname))
            self._gates_comp.add(component)
            components_dict[cellname] = component

        vdd = VDD(self._circuit)
        self._gates_comp.add(vdd)
        components_dict["VDD"] = vdd
        gnd = GND(self._circuit)
        self._gates_comp.add(gnd)
        components_dict["GND"] = gnd

        return components_dict

    def _connect_sinks(self, components_dict, src_comp_port, sinks):
        """Connect a source port to multiple sinks"""
        for sink_port in sinks:
            if isinstance(sink_port.parent, YosysModule):
                # Connect cell output to module top
                dst_port = self.port(sink_port.name).get_bit(sink_port.bit_index)
                src_comp_port.wire = dst_port
            else:
                # Connect cell output to cell input
                dst_comp = components_dict[sink_port.parent_name]
                src_comp_port.wire = dst_comp.port(sink_port.name)

    def _connect_cells(self, components_dict):
        """Connect all cells"""
        for net, source in self._netlist_nets.source.items():
            if isinstance(source.parent, YosysModule):
                # Only connect cells here
                continue
            if isinstance(source.parent, YosysCell):
                src_comp = components_dict[source.parent_name]
                self._connect_sinks(
                    components_dict, src_comp.port(source.name), self._netlist_nets.sinks[net]
                )

        gnd_sinks = self._netlist_nets.sinks.get("0", [])
        self._connect_sinks(components_dict, components_dict["GND"].port("O"), gnd_sinks)
        vdd_sinks = self._netlist_nets.sinks.get("1", [])
        self._connect_sinks(components_dict, components_dict["VDD"].port("O"), vdd_sinks)

    def _connect_external_input_port(self, components_dict, portname, port_dict):
        """Connect external input port"""
        for bit_idx, net in enumerate(port_dict.bits):
            for sink_port in self._netlist_nets.sinks[net]:
                if isinstance(sink_port.parent, YosysModule):
                    # Connect module input to module output
                    dst_port = self.port(sink_port.name).get_bit(sink_port.bit_index)
                    self.port(portname).get_bit(bit_idx).wire = dst_port
                else:
                    # Connect module input to cell input
                    self._connect_sinks(
                        components_dict, self.port(portname).get_bit(bit_idx), [sink_port]
                    )

    def _connect_external_input(self, components_dict):
        """Connect all external input ports"""
        for portname, port_dict in self._netlist_module.ports.items():
            if port_dict.direction == "output":
                continue
            self._connect_external_input_port(components_dict, portname, port_dict)

    def _create_component(self):
        """Create yosys component"""
        # Create cells
        components_dict = self._create_cells()
        # Connect cells
        self._connect_cells(components_dict)
        # Connect external input ports
        self._connect_external_input(components_dict)

    def _synth_verilog(self):
        """Synthesize verilog to netlist"""
        modules = Synthesis.list_modules(self._path)
        if len(modules) == 1:
            toplevel = modules[0]
        else:
            raise YosysComponentException("Current only one module per verilog file is supported")

        synthesis = Synthesis(self._path, toplevel)
        return synthesis.synth_to_dict(silent=True)

    def _load_netlist_dict(self):
        """Load yosys netlist dict"""
        if self._path.endswith(".json"):
            with open(self._path, encoding="utf-8") as json_file:
                netlist_dict = json.load(json_file)
        elif self._path.endswith(".v"):
            netlist_dict = self._synth_verilog()
        else:
            raise YosysComponentException(f"Unknown file extension '{self._path}'")

        yosys_netlist = YosysNetlist(**netlist_dict)
        modules = yosys_netlist.get_modules()

        if len(modules) > 1:
            raise YosysComponentException("Only one module per file is supported")

        return yosys_netlist

    def _load_file(self):
        """Load yosys verilog/json-netlist file"""
        yosys_netlist = self._load_netlist_dict()
        self.create_from_netlist(yosys_netlist)

    def reload_file(self):
        """Reload yosys verilog/json-netlist file"""
        yosys_netlist = self._load_netlist_dict()
        self.reload_from_netlist(yosys_netlist)

    def _disconnect_external_ports(self):
        """Disconnect external ports before reload"""
        for port in self.inports():
            for bit_id in range(port.width):
                bit_port = port.get_bit(bit_id)
                bit_port.remove_wires()
        for port in self.outports():
            for bit_id in range(port.width):
                bit_port = port.get_bit(bit_id)
                bit_port.set_driver(None)

    def settings_to_dict(self):
        path = self.circuit.store_path(self._path)
        return {"path": path}

    @classmethod
    def get_parameters(cls):
        return {
            "path": {
                "type": "path",
                "fileinfo": "Yosys JSON Netlist (*.json);;Verilog File (*.v)",
                "description": "Select verilog file or Yosys json netlist",
            }
        }
