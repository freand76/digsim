# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

"""
Module with classes to create a yosys component
from a yosys json netlist.
"""

# pylint: disable=protected-access
# pylint: disable=too-many-instance-attributes

import json

import digsim.circuit.components._yosys_atoms

from .atoms import Component, MultiComponent, PortMultiBitWire, PortOut


class YosysComponentException(Exception):
    """Yosys component exception class"""


class StaticLevels(Component):
    """Yosys component for static logic levels"""

    def __init__(self, circuit, name):
        super().__init__(circuit, name)
        self.add_port(PortOut(self, "low"))
        self.add_port(PortOut(self, "high"))

    def init(self):
        self.low.value = 0
        self.high.value = 1


class YosysComponent(MultiComponent):
    """Class to create a yosys component from a yosys json netlist"""

    def __init__(self, circuit, name="Yosys", path=None, nets=True):
        super().__init__(circuit, name)
        self._circuit = circuit
        self._path = path
        self._nets = nets
        self._port_connections = {}
        self._json = None
        self._yosys_name = None
        self._gates_comp = None
        self._net_comp = None

        self._setup_base()

        if nets:
            self._net_comp = Component(self._circuit, "nets")
            self.add(self._net_comp)

        if self._path is not None:
            self.load(self._path)

    def _setup_base(self):
        self._gates_comp = MultiComponent(self._circuit, "gates")
        self.add(self._gates_comp)
        static_levels = StaticLevels(self._circuit, "StaticLevels")
        self._gates_comp.add(static_levels)
        self._add_port("0", static_levels.low, driver=True)
        self._add_port("1", static_levels.high, driver=True)

    def load(self, filename):
        """Load yosys json netlist file"""
        self._path = filename
        with open(self._path, encoding="utf-8") as json_file:
            self._json = json.load(json_file)
        self._yosys_name = self._get_component_name()
        # self.set_name(self._yosys_name)
        self.set_display_name(self._yosys_name)
        self._parse_cells()
        self._make_cell_connections()
        self._connect_external_ports()
        self._add_netnames()

    def _add_port(self, connection_id, port_instance, driver=False):
        if self._port_connections.get(connection_id) is None:
            self._port_connections[connection_id] = {"src": None, "dst": []}
        if driver:
            self._port_connections[connection_id]["src"] = port_instance
        else:
            self._port_connections[connection_id]["dst"].append(port_instance)

    def _get_component_name(self):
        modules = self._json["modules"]
        if len(modules) > 1:
            raise YosysComponentException("Only one module per file is supported")
        return list(modules.keys())[0]

    def _parse_cells(self):
        cells = self._json["modules"][self._yosys_name]["cells"]
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

    def _connect_external_port(self, portname, port_dict, port_is_output):
        port_width = len(port_dict["bits"])
        external_port = PortMultiBitWire(self, portname, width=port_width, output=port_is_output)
        for idx, connection_id in enumerate(port_dict["bits"]):
            port_instance = self._port_connections[connection_id]["src"]
            if port_is_output:
                port_instance.wire = external_port.get_bit(idx)
                continue

            portlist = self._port_connections[connection_id]["dst"]
            for port in portlist:
                external_port.get_bit(idx).wire = port
                self._add_port(connection_id, external_port.get_bit(idx), driver=True)
        self.add_port(external_port)

    def _connect_external_ports(self):
        ports = self._json["modules"][self._yosys_name]["ports"]
        for portname, port_dict in ports.items():
            port_is_output = port_dict["direction"] == "output"
            self._connect_external_port(portname, port_dict, port_is_output)

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

    def _add_netnames(self):
        if self._net_comp is None:
            return

        netnames = self._json["modules"][self._yosys_name]["netnames"]
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
                "fileinfo": "Yosys JSON Netlist (*.json)",
                "description": "Select yosys json component",
            }
        }
