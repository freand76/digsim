import json

from components import Component, InputPort, OutputPort, SignalLevel


class JsonComponentException(Exception):
    pass


class JsonComponent(Component):
    def __init__(self, filename):
        self._filename = filename

        with open(self._filename) as f:
            self._json = json.load(f)

        super().__init__(self._get_component_name())
        port_tag_dict = self._parse_ports()

        print("IN:", self.inports)
        print("OUT:", self.outports)
        print("TAG:", port_tag_dict)

        self._parse_cells()

    def _get_component_name(self):
        modules = self._json["modules"]
        if len(modules) > 1:
            raise JsonComponentException("Only one module per file is supported")
        return list(modules.keys())[0]

    def _parse_ports(self):
        port_tag_dict = {}
        ports = self._json["modules"][self.name]["ports"]
        for portname, port_dict in ports.items():
            if port_dict["direction"] == "input":
                PortClass = InputPort
            else:
                PortClass = OutputPort

            for idx, bit in enumerate(port_dict["bits"]):
                if len(port_dict["bits"]) == 1:
                    portbitname = f"{portname}"
                else:
                    portbitname = f"{portname}{idx}"
                port_instance = PortClass(self)
                self.add_port(portbitname, port_instance)

                port_tag_dict[bit] = port_instance
        return port_tag_dict

    def _parse_cells(self):
        cells = self._json["modules"][self.name]["cells"]
        for cellname, cell_dict in cells.items():
            print(cellname, cell_dict["type"])
