# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

# pylint: disable=protected-access

import json

import digsim.circuit.components._yosys_atoms

from .atoms import BusInPort, BusOutPort, ComponentPort, MultiComponent, PortDirection


class YosysComponentException(Exception):
    pass


class YosysComponent(MultiComponent):
    def __init__(self, circuit, name="Yosys", filename=None):
        super().__init__(circuit, name)
        self._filename = filename
        self._port_tag_dict = {}
        self._circuit = circuit
        self._component_id = {}
        self._json = None
        self._yosys_name = None
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
        for _, cell_dict in cells.items():
            cell_type = cell_dict["type"]
            cell_name = cell_type[2:-1]
            component_class_name = f"_{cell_name}_"
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
                else:
                    external_port = BusOutPort(self, portbitname, width=port_width)
                    for idx, connection_id in enumerate(port_dict["bits"]):
                        portlist = self._port_tag_dict[connection_id]
                        port_iotype = [port.direction == PortDirection.OUT for port in portlist]
                        out_index = port_iotype.index(True)
                        port_instance = portlist[out_index]
                        external_port.connect_bit(idx, port_instance)
                self.add_port(external_port)

    def setup(self, path=None):
        if path is not None:
            self.load(path)

    def settings_to_dict(self):
        return {"path": self._filename}
