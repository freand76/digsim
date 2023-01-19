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
    def __init__(self, circuit, name="Yosys", filename=None):
        super().__init__(circuit, name)
        self._filename = filename
        self._port_tag_dict = {}
        self._external_ports = {}
        self._circuit = circuit
        self._component_id = {}
        self._json = None
        self._yosys_name = None
        self._logic_one = StaticLogic(circuit, "LogicOne", SignalLevel.HIGH)
        self.add(self._logic_one)
        self._logic_zero = StaticLogic(circuit, "LogicZero", SignalLevel.LOW)
        self.add(self._logic_zero)
        if filename is not None:
            self.load(filename)

    def load(self, filename):
        self._filename = filename
        with open(self._filename, encoding="utf-8") as json_file:
            self._json = json.load(json_file)
        self._yosys_name = self._get_component_name()
        self.display_name = self._yosys_name
        self._parse_cells()
        self._make_cell_connections()
        self._connect_external_ports()
        self._connect_netnames()

    def _add_connection(self, connection_id, port_instance):
        if self._port_tag_dict.get(connection_id) is None:
            self._port_tag_dict[connection_id] = []
        self._port_tag_dict[connection_id].append(port_instance)

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
            self.add(component)
            cell_connections = cell_dict["connections"]
            for portname, connection in cell_connections.items():
                if len(connection) > 1:
                    raise Exception(f"Cannot handle multibit connection for cell '{cell_type}'")
                connection_id = connection[0]
                if connection_id == "1":
                    self._logic_one.O.wire = component.port(portname)
                elif connection_id == "0":
                    self._logic_zero.O.wire = component.port(portname)
                else:
                    port_instance = component.port(portname)
                    self._add_connection(connection_id, port_instance)

    def _make_cell_connections(self):
        for _, portlist in self._port_tag_dict.items():
            is_outport_list = [port.direction == PortDirection.OUT for port in portlist]
            if any(is_outport_list):
                out_index = is_outport_list.index(True)
                out_port = portlist[out_index]
                for port in portlist:
                    if port.direction == PortDirection.IN:
                        out_port.wire = port

    def _connect_external_ports(self):
        ports = self._json["modules"][self._yosys_name]["ports"]
        for portname, port_dict in ports.items():
            port_direction = (
                PortDirection.IN if port_dict["direction"] == "input" else PortDirection.OUT
            )
            portbitname = f"{portname}"
            port_width = len(port_dict["bits"])
            if port_width == 1:
                connection_id = port_dict["bits"][0]
                if connection_id not in self._port_tag_dict:
                    print(f"Skipping non-connected port '{portname}'")
                    continue
                portlist = self._port_tag_dict[connection_id]
                external_port = ComponentPort(self, portbitname, port_direction)
                self.add_port(external_port)
                if port_direction == PortDirection.IN:
                    self._external_ports[connection_id] = external_port
                    for port in portlist:
                        external_port.wire = port
                else:
                    port_iotype = [port.direction == PortDirection.OUT for port in portlist]
                    out_index = port_iotype.index(True)
                    port_instance = portlist[out_index]
                    port_instance.wire = external_port

            else:
                if port_direction == PortDirection.IN:
                    external_port = BusInPort(self, portbitname, width=port_width)
                    for idx, connection_id in enumerate(port_dict["bits"]):
                        portlist = self._port_tag_dict[connection_id]
                        for port in portlist:
                            external_port.connect_bit(idx, port)
                            self._external_ports[connection_id] = external_port.port_bit(idx)
                else:
                    external_port = BusOutPort(self, portbitname, width=port_width)
                    for idx, connection_id in enumerate(port_dict["bits"]):
                        portlist = self._port_tag_dict[connection_id]
                        port_iotype = [port.direction == PortDirection.OUT for port in portlist]
                        out_index = port_iotype.index(True)
                        port_instance = portlist[out_index]
                        external_port.connect_bit(idx, port_instance)
                self.add_port(external_port)

    def _connect_netnames(self):
        net_comp = Component(self._circuit, "000_internal_net")
        self.add(net_comp)
        netnames = self._json["modules"][self._yosys_name]["netnames"]
        for netname, netname_dict in netnames.items():
            if netname_dict["hide_name"] == 0:
                netname = netname.replace(".", "_")
                net_width = len(netname_dict["bits"])
                if net_width == 1:
                    connection_id = netname_dict["bits"][0]
                    net_port = ComponentPort(net_comp, f"{netname}", PortDirection.IN)
                    net_comp.add_port(net_port)
                    if connection_id == "0":
                        port_instance = self._logic_zero.port("O")
                    elif connection_id == "1":
                        port_instance = self._logic_one.port("O")
                    elif connection_id in self._external_ports:
                        port_instance = self._external_ports[connection_id]
                    elif connection_id in self._port_tag_dict:
                        portlist = self._port_tag_dict[connection_id]
                        port_iotype = [port.direction == PortDirection.OUT for port in portlist]
                        out_index = port_iotype.index(True)
                        port_instance = portlist[out_index]
                    else:
                        continue
                    port_instance.wire = net_port
                else:
                    net_port = BusOutPort(net_comp, f"{netname}", width=net_width)
                    net_comp.add_port(net_port)
                    for idx, connection_id in enumerate(netname_dict["bits"]):
                        if connection_id == "0":
                            port_instance = self._logic_zero.port("O")
                        elif connection_id == "1":
                            port_instance = self._logic_one.port("O")
                        elif connection_id in self._external_ports:
                            port_instance = self._external_ports[connection_id]
                        elif connection_id in self._port_tag_dict:
                            portlist = self._port_tag_dict[connection_id]
                            port_iotype = [
                                port.direction == PortDirection.OUT for port in portlist
                            ]
                            out_index = port_iotype.index(True)
                            port_instance = portlist[out_index]
                        else:
                            continue
                        net_port.connect_bit(idx, port_instance)

    def setup(self, path=None):
        if path is not None:
            self.load(path)

    def settings_to_dict(self):
        return {"path": self._filename}
