import json

from ._component import MultiComponent
from ._gates import ALDFFE_PPP, AND, DFFE_PP0P, NOT, XOR
from ._port import BusInPort, BusOutPort, ComponentPort, PortDirection


class JsonComponentException(Exception):
    pass


class JsonComponent(MultiComponent):

    COMPONENT_MAP = {
        "$_NOT_": {"class": NOT, "name": "not"},
        "$_AND_": {"class": AND, "name": "and"},
        "$_XOR_": {"class": XOR, "name": "xor"},
        "$_DFFE_PP0P_": {"class": DFFE_PP0P, "name": "dffe_pp0p"},
        "$_ALDFFE_PPP_": {"class": ALDFFE_PPP, "name": "aldffe_ppp"},
    }

    def __init__(self, circuit, filename):
        self._filename = filename
        self._port_tag_dict = {}
        self._circuit = circuit
        self._component_id = {}
        with open(self._filename, encoding="utf-8") as json_file:
            self._json = json.load(json_file)

        super().__init__(circuit, self._get_component_name())
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
            raise JsonComponentException("Only one module per file is supported")
        return list(modules.keys())[0]

    def _parse_cells(self):
        cells = self._json["modules"][self.name]["cells"]
        for _, cell_dict in cells.items():
            cell_type = cell_dict["type"]
            cell = self.COMPONENT_MAP.get(cell_type)
            if cell is None:
                raise Exception(f"Cell '{cell_type}' not implemented yet...")
            component_class = cell["class"]
            cell_count = self._component_id.get(cell["name"], 0)
            self._component_id[cell["name"]] = cell_count + 1
            component = component_class(self._circuit, name=f"{cell['name']}_{cell_count}")
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
        ports = self._json["modules"][self.name]["ports"]
        for portname, port_dict in ports.items():
            port_direction = (
                PortDirection.IN if port_dict["direction"] == "input" else PortDirection.OUT
            )
            portbitname = f"{portname}"
            port_width = len(port_dict["bits"])
            if port_width == 1:
                connection_id = port_dict["bits"][0]
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
