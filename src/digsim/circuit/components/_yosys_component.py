# Copyright (c) Fredrik Andersson, 2023-2024
# All rights reserved

"""
Module with classes to create a yosys component
from a yosys json netlist.
"""

import json

import digsim.circuit.components._yosys_atoms
from digsim.synth import Synthesis
from digsim.utils import YosysNetlist

from .atoms import Component, DigsimException, MultiComponent, PortMultiBitWire


class YosysComponentException(DigsimException):
    """Yosys component exception class"""


class YosysComponent(MultiComponent):
    """Class to create a yosys component from a yosys json netlist"""

    def __init__(self, circuit, path=None, name=None, nets=True):
        super().__init__(circuit, name)
        self._circuit = circuit
        self._path = path
        self._gates_comp = None
        self._net_comp = None
        self._netlist_module = None
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
        # Set Name
        self.set_name(module_name)
        self.set_display_name(module_name)
        # Add External Ports
        for portname, port_dict in self._netlist_module.get_external_interface().items():
            external_port = PortMultiBitWire(
                self, portname, width=len(port_dict["nets"]), output=not port_dict["output"]
            )
            self.add_port(external_port)
        # Create component
        self._create_component()

    def reload_from_netlist(self, netlist_object):
        """Reload netlist from netlist object"""
        modules = netlist_object.get_modules()
        module_name = list(modules.keys())[0]
        reload_module = netlist_object.get_modules()[module_name]

        # Verify that new external interface is the same as the current
        current_ext_if = self._netlist_module.get_external_interface()
        new_ext_if = reload_module.get_external_interface()

        if current_ext_if.keys() != new_ext_if.keys():
            raise YosysComponentException("Yosys component interface differs")
        for key, _ in current_ext_if.items():
            if len(current_ext_if[key]["nets"]) != len(new_ext_if[key]["nets"]):
                raise YosysComponentException("Yosys component interface differs")
            if current_ext_if[key]["output"] != new_ext_if[key]["output"]:
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
        # Create component
        self._create_component()

    def _create_cells(self):
        """Create cells in component"""
        components_dict = {}
        for cellname, cell in self._netlist_module.get_cells().items():
            component_class = getattr(
                digsim.circuit.components._yosys_atoms, cell.get_friendly_type()
            )
            component = component_class(self._circuit, name=cell.get_friendly_name())
            self._gates_comp.add(component)
            components_dict[cellname] = component
        return components_dict

    def _connect_cell_port(self, components_dict, src_cell, source_port):
        """Connect cell ports"""
        src_comp = components_dict[src_cell.name()]
        src_comp_port = src_comp.port(source_port.name())
        net = source_port.get_nets()[0]
        for sink_port in source_port.get_sinks():
            if sink_port.get_parent().get_type() == "module":
                # Connect cell output to module top
                for dst_bit, sink_net in enumerate(sink_port.get_nets()):
                    if net == sink_net:
                        dst_port = self.port(sink_port.name()).get_bit(dst_bit)
                        src_comp_port.wire = dst_port
            else:
                # Connect cell output to cell input
                dst_comp = components_dict[sink_port.get_parent().name()]
                src_comp_port.wire = dst_comp.port(sink_port.name())

    def _connect_cells(self, components_dict):
        """Connect all cells"""
        for _, src_cell in self._netlist_module.get_cells().items():
            for source_port in src_cell.get_source_ports():
                self._connect_cell_port(components_dict, src_cell, source_port)

    def _connect_external_input_port(self, components_dict, portname, port_dict):
        """Conenct external input port"""
        for bit_idx, net in enumerate(port_dict["nets"]):
            for sink_port in self._netlist_module.get_sinks(net):
                if sink_port.get_parent().get_type() == "module":
                    # Connect module input to module output
                    for dst_bit, sink_net in enumerate(sink_port.get_nets()):
                        if net == sink_net:
                            dst_port = self.port(sink_port.name()).get_bit(dst_bit)
                            self.port(portname).get_bit(bit_idx).wire = dst_port
                else:
                    # Connect module input to cell input
                    dst_comp = components_dict[sink_port.get_parent().name()]
                    self.port(portname).get_bit(bit_idx).wire = dst_comp.port(sink_port.name())

    def _connect_external_input(self, components_dict):
        """Connect all external input ports"""
        for portname, port_dict in self._netlist_module.get_external_interface().items():
            if not port_dict["output"]:
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

        yosys_netlist = YosysNetlist()
        yosys_netlist.from_dict(netlist_dict)
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
