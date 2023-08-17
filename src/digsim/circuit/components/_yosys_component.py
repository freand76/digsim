# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

"""
Module with classes to create a yosys component
from a yosys json netlist.
"""

# pylint: disable=protected-access
# pylint: disable=too-many-instance-attributes

import json
import os
import tempfile

import digsim.circuit.components._yosys_atoms
from digsim.synth import Synthesis

from .atoms import Component, DigsimException, MultiComponent, PortMultiBitWire, PortOutDelta


class YosysComponentException(DigsimException):
    """Yosys component exception class"""


class StaticLevels(Component):
    """Yosys component for static logic levels"""

    def __init__(self, circuit, name):
        super().__init__(circuit, name)
        self.add_port(PortOutDelta(self, "low"))
        self.add_port(PortOutDelta(self, "high"))

    def init(self):
        self.low.value = 0
        self.high.value = 1


class YosysComponent(MultiComponent):
    """Class to create a yosys component from a yosys json netlist"""

    def __init__(self, circuit, path=None, name=None, nets=True):
        super().__init__(circuit, name)
        self._circuit = circuit
        self._path = path
        self._nets = nets
        self._yosys_name = None
        self._gates_comp = None
        self._net_comp = None
        self._port_connections = None
        self._external_interface = None
        self._setup_base()

        if nets:
            self._net_comp = Component(self._circuit, "nets")
            self.add(self._net_comp)

        self._load_file()

    def _setup_base(self):
        self._gates_comp = MultiComponent(self._circuit, "gates")
        self.add(self._gates_comp)

    def _get_external_interface(self, netlist_dict):
        external_interface = {}
        ports = netlist_dict["modules"][self._yosys_name]["ports"]
        for portname, port_dict in ports.items():
            ext_port = {"width": len(port_dict["bits"]), "dir": port_dict["direction"]}
            external_interface[portname] = ext_port
        return external_interface

    def _setup_from_netlist(self, netlist_dict, reload_netlist=False):
        self._port_connections = {}
        static_levels = StaticLevels(self._circuit, "StaticLevels")
        self._gates_comp.add(static_levels)
        self._add_port("0", static_levels.low, driver=True)
        self._add_port("1", static_levels.high, driver=True)
        self._parse_cells(netlist_dict)
        self._make_cell_connections()
        self._connect_external_ports(netlist_dict, reload_netlist)
        self._add_netnames(netlist_dict)

    def _create_from_dict(self, netlist_dict):
        self._yosys_name = self._get_component_name(netlist_dict)
        self.set_name(self._yosys_name)
        self.set_display_name(self._yosys_name)
        self._external_interface = self._get_external_interface(netlist_dict)
        self._setup_from_netlist(netlist_dict)

    def _reload_from_dict(self, netlist_dict):
        external_interface = self._get_external_interface(netlist_dict)
        if external_interface != self._external_interface:
            raise YosysComponentException("Yosys component interface differs")
        # Disconnect ports
        self._disconnect_external_ports()
        # Remove yosys atoms
        self._gates_comp.remove_all_components()
        # Remove nets
        if self._net_comp is not None:
            self._net_comp.delete_all_ports()
        # Setup netlist
        self._setup_from_netlist(netlist_dict, reload_netlist=True)

    def _synth_verilog(self):
        modules = Synthesis.list_modules(self._path)
        if len(modules) == 1:
            toplevel = modules[0]
        else:
            raise YosysComponentException("Current only one module per verilog file is supported")

        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            filename = tmp_file.name
        synthesis = Synthesis(self._path, filename, toplevel)
        if not synthesis.execute():
            raise YosysComponentException("Yosys synthesis error")
        return filename

    def _load_netlist_dict(self):
        unlink_file = False
        if self._path.endswith(".json"):
            filename = self._path
        elif self._path.endswith(".v"):
            filename = self._synth_verilog()
            unlink_file = True
        else:
            raise YosysComponentException(f"Unknown file extension '{self._path}'")

        with open(filename, encoding="utf-8") as json_file:
            netlist_dict = json.load(json_file)

        if unlink_file:
            os.unlink(filename)

        return netlist_dict

    def _load_file(self):
        """Load yosys verilog/json-netlist file"""
        netlist_dict = self._load_netlist_dict()
        self._create_from_dict(netlist_dict)

    def reload_file(self):
        """Reload yosys verilog/json-netlist file"""
        netlist_dict = self._load_netlist_dict()
        self._reload_from_dict(netlist_dict)

    def _add_port(self, connection_id, port_instance, driver=False):
        if self._port_connections.get(connection_id) is None:
            self._port_connections[connection_id] = {"src": None, "dst": []}
        if driver:
            self._port_connections[connection_id]["src"] = port_instance
        else:
            self._port_connections[connection_id]["dst"].append(port_instance)

    def _get_component_name(self, netlist_dict):
        modules = netlist_dict["modules"]
        if len(modules) > 1:
            raise YosysComponentException("Only one module per file is supported")
        return list(modules.keys())[0]

    def _parse_cells(self, netlist_dict):
        cells = netlist_dict["modules"][self._yosys_name]["cells"]
        for cell, cell_dict in cells.items():
            cell_type = cell_dict["type"]
            cell_name = f'{cell.split("$")[-1]}_{cell_type[2:-1]}'
            component_class_name = f"_{cell_type[2:-1]}_"
            component_class = getattr(digsim.circuit.components._yosys_atoms, component_class_name)
            component = component_class(self._circuit, name=f"{cell_name}")
            self._gates_comp.add(component)

            for portname, direction in cell_dict["port_directions"].items():
                connection_id = cell_dict["connections"][portname][0]
                port_instance = component.port(portname)
                if connection_id in ["0", "1"]:
                    self._port_connections[connection_id]["src"].wire = port_instance
                else:
                    driver = direction == "output"
                    self._add_port(connection_id, port_instance, driver=driver)

    def _make_cell_connections(self):
        for _, src_dst_dict in self._port_connections.items():
            driver_port = src_dst_dict["src"]
            if driver_port is None:
                continue
            for port in src_dst_dict["dst"]:
                driver_port.wire = port

    def _disconnect_external_ports(self):
        for port in self.inports():
            for bit_id in range(port.width):
                bit_port = port.get_bit(bit_id)
                bit_port.remove_wires()
        for port in self.outports():
            for bit_id in range(port.width):
                bit_port = port.get_bit(bit_id)
                bit_port.set_driver(None)

    def _connect_external_port(self, portname, port_dict, port_is_output, reload_netlist=False):
        port_width = len(port_dict["bits"])
        if reload_netlist:
            external_port = self.port(portname)
        else:
            external_port = PortMultiBitWire(
                self, portname, width=port_width, output=port_is_output
            )
        for idx, connection_id in enumerate(port_dict["bits"]):
            connection_id_dict = self._port_connections.get(connection_id)
            if connection_id_dict is None:
                continue
            port_instance = connection_id_dict["src"]
            if port_is_output:
                port_instance.wire = external_port.get_bit(idx)
                continue

            portlist = connection_id_dict["dst"]
            for port in portlist:
                external_port.get_bit(idx).wire = port
                self._add_port(connection_id, external_port.get_bit(idx), driver=True)
        if not reload_netlist:
            self.add_port(external_port)

    def _connect_external_ports(self, netlist_dict, reload_netlist=False):
        ports = netlist_dict["modules"][self._yosys_name]["ports"]
        for portname, port_dict in ports.items():
            port_is_output = port_dict["direction"] == "output"
            self._connect_external_port(portname, port_dict, port_is_output, reload_netlist)

    def _add_netname(self, netname, netname_dict):
        netname_valid = False
        for idx, connection_id in enumerate(netname_dict["bits"]):
            if connection_id not in self._port_connections:
                continue
            netname_valid = True

        if not netname_valid:
            return

        net_width = len(netname_dict["bits"])
        net_port = PortMultiBitWire(self._net_comp, f"{netname}", width=net_width)
        self._net_comp.add_port(net_port)
        for idx, connection_id in enumerate(netname_dict["bits"]):
            if connection_id in self._port_connections:
                port_instance = self._port_connections[connection_id]["src"]
                port_instance.wire = net_port.get_bit(idx)

    def _add_netnames(self, netlist_dict):
        if self._net_comp is None:
            return

        netnames = netlist_dict["modules"][self._yosys_name]["netnames"]
        for netname, netname_dict in netnames.items():
            if netname_dict["hide_name"] != 0:
                continue
            netname = netname.replace(".", "_")
            self._add_netname(netname, netname_dict)

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
