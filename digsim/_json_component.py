import json

from ._base import InputPort, MultiComponent
from ._gates import AND, DFFE_PP0P, NOT, XOR


class JsonComponentException(Exception):
    pass


class JsonComponent(MultiComponent):

    COMPONENT_MAP = {
        "$_NOT_": {"class": NOT, "name": "not"},
        "$_AND_": {"class": AND, "name": "and"},
        "$_XOR_": {"class": XOR, "name": "xor"},
        "$_DFFE_PP0P_": {"class": DFFE_PP0P, "name": "dffe_pp0p"},
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
            ComponentClass = cell["class"]
            cell_count = self._component_id.get(cell["name"], 0)
            self._component_id[cell["name"]] = cell_count + 1
            component = ComponentClass(
                self._circuit, name=f"{cell['name']}_{cell_count}"
            )
            self.add(component)
            cell_connections = cell_dict["connections"]
            for portname, connection in cell_connections.items():

                if len(connection) > 1:
                    raise Exception(
                        f"Cannot handle multibit connection for cell '{cell_type}'"
                    )
                connection_id = connection[0]
                port_instance = component.port(portname)
                self._add_connection(connection_id, port_instance)

    def _make_cell_connections(self):
        for _, portlist in self._port_tag_dict.items():
            is_outport_list = [port.is_outport for port in portlist]
            if any(is_outport_list):
                out_index = is_outport_list.index(True)
                out_port = portlist[out_index]
                for port in portlist:
                    if not port.is_outport:
                        out_port.wire = port

    def _connect_external_ports(self):
        ports = self._json["modules"][self.name]["ports"]
        for portname, port_dict in ports.items():
            is_input_port = port_dict["direction"] == "input"
            for idx, connection_id in enumerate(port_dict["bits"]):
                if len(port_dict["bits"]) == 1:
                    portbitname = f"{portname}"
                else:
                    portbitname = f"{portname}{idx}"
                portlist = self._port_tag_dict[connection_id]
                external_port = InputPort(self)
                self.add_port(portbitname, external_port)
                if is_input_port:
                    for port in portlist:
                        external_port.wire = port
                else:
                    port_iotype = [port.is_outport for port in portlist]
                    out_index = port_iotype.index(True)
                    port_instance = portlist[out_index]
                    port_instance.wire = external_port