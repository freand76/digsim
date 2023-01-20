# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

# pylint: disable=protected-access
# pylint: disable=too-many-instance-attributes

import json

import digsim.circuit.components._yosys_atoms

from .atoms import (
    BusInPort,
    BusOutPort,
    Component,
    ComponentPort,
    MultiComponent,
    OutputPort,
    PortDirection,
    SignalLevel,
)


class YosysComponentException(Exception):
    pass


class StaticLogic(Component):
    def __init__(self, circuit, name, level):
        super().__init__(circuit, name)
        self.add_port(OutputPort(self, "O"))
        self._level = level

    def init(self):
        self.O.level = self._level


class YosysComponent(MultiComponent):
    def __init__(self, circuit, name="Yosys", filename=None, nets=True):
        super().__init__(circuit, name)
        self._gates_comp = MultiComponent(self._circuit, "gates")
        self.add(self._gates_comp)
        self._net_comp = None
        self._filename = filename
        self._nets = nets
        self._port_connections = {}
        self._circuit = circuit
        self._component_id = {}
        self._json = None
        self._yosys_name = None
        self._add_logic_one_and_zero()

        if nets:
            self._net_comp = Component(self._circuit, "nets")
            self.add(self._net_comp)

        if filename is not None:
            self.load(filename)

    def _add_logic_one_and_zero(self):
        self._logic_one = StaticLogic(self._circuit, "LogicOne", SignalLevel.HIGH)
        self._gates_comp.add(self._logic_one)
        self._add_port("1", self._logic_one.O, driver=True)
        self._logic_zero = StaticLogic(self._circuit, "LogicZero", SignalLevel.LOW)
        self._gates_comp.add(self._logic_zero)
        self._add_port("0", self._logic_zero.O, driver=True)

    def load(self, filename):
        self._filename = filename
        with open(self._filename, encoding="utf-8") as json_file:
            self._json = json.load(json_file)
        self._yosys_name = self._get_component_name()
        self.name = self._yosys_name
        self.display_name = self._yosys_name
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
            cell_count = self._component_id.get(cell_name, 0)
            self._component_id[cell_name] = cell_count + 1
            component = component_class(self._circuit, name=f"{cell_name}_{cell_count}")
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

    def _connect_external_bit_port(self, portname, port_dict, port_direction):
        connection_id = port_dict["bits"][0]
        if connection_id not in self._port_connections:
            print(f"Skipping non-connected port '{portname}'")
            return
        portlist = self._port_connections[connection_id]["dst"]
        external_port = ComponentPort(self, portname, port_direction)
        self.add_port(external_port)
        if port_direction == PortDirection.IN:
            for port in portlist:
                external_port.wire = port
                self._add_port(connection_id, external_port, driver=True)
        else:
            port_instance = self._port_connections[connection_id]["src"]
            port_instance.wire = external_port

    def _connect_external_bus_port(self, portname, port_dict, port_direction, port_width):
        if port_direction == PortDirection.IN:
            external_port = BusInPort(self, portname, width=port_width)
            for idx, connection_id in enumerate(port_dict["bits"]):
                portlist = self._port_connections[connection_id]["dst"]
                for port in portlist:
                    external_port.connect_bit(idx, port)
                    self._add_port(connection_id, external_port.port_bit(idx), driver=True)
        else:
            external_port = BusOutPort(self, portname, width=port_width)
            for idx, connection_id in enumerate(port_dict["bits"]):
                port_instance = self._port_connections[connection_id]["src"]
                external_port.connect_bit(idx, port_instance)
        self.add_port(external_port)

    def _connect_external_ports(self):
        ports = self._json["modules"][self._yosys_name]["ports"]
        for portname, port_dict in ports.items():
            port_direction = (
                PortDirection.IN if port_dict["direction"] == "input" else PortDirection.OUT
            )
            port_width = len(port_dict["bits"])
            if port_width == 1:
                self._connect_external_bit_port(portname, port_dict, port_direction)
            else:
                self._connect_external_bus_port(portname, port_dict, port_direction, port_width)

    def _add_bit_netname(self, netname, netname_dict):
        connection_id = netname_dict["bits"][0]
        if connection_id in self._port_connections:
            net_port = ComponentPort(self._net_comp, f"{netname}", PortDirection.IN)
            self._net_comp.add_port(net_port)
            port_instance = self._port_connections[connection_id]["src"]
            port_instance.wire = net_port

    def _add_bus_netname(self, netname, netname_dict, net_width):
        netname_valid = False
        for idx, connection_id in enumerate(netname_dict["bits"]):
            if connection_id not in self._port_connections:
                continue
            netname_valid = True

        if not netname_valid:
            return

        net_port = BusOutPort(self._net_comp, f"{netname}", width=net_width)
        self._net_comp.add_port(net_port)
        for idx, connection_id in enumerate(netname_dict["bits"]):
            if connection_id in self._port_connections:
                port_instance = self._port_connections[connection_id]["src"]
                net_port.connect_bit(idx, port_instance)

    def _add_netnames(self):
        if self._net_comp is None:
            return

        netnames = self._json["modules"][self._yosys_name]["netnames"]
        for netname, netname_dict in netnames.items():
            if netname_dict["hide_name"] != 0:
                continue
            netname = netname.replace(".", "_")
            net_width = len(netname_dict["bits"])
            if net_width == 1:
                self._add_bit_netname(netname, netname_dict)
            else:
                self._add_bus_netname(netname, netname_dict, net_width)

    def setup(self, path=None):
        if path is not None:
            self.load(path)

    def settings_to_dict(self):
        return {"path": self._filename}
