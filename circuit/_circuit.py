import json

from components import Component


class CircuitError(Exception):
    pass


class Circuit:
    def __init__(self):
        self._components = []

    def init(self):
        for comp in self._components:
            comp.init()

    def add_component(self, component):
        for comp in self._components:
            if component.name == comp.name:
                raise CircuitError("Component already in circuit")
        self._components.append(component)

    def get_component(self, component_name):
        for comp in self._components:
            if component_name == comp.name:
                return comp
        raise CircuitError(f"Component '{component_name}' not found")

    def from_json_file(self, filename):
        with open(filename) as f:
            json_file = json.load(f)

        json_circuit = json_file["circuit"]
        json_components = json_circuit["components"]
        json_connections = json_circuit["connections"]

        for json_component in json_components:
            c = Component.from_json(json_component)
            self.add_component(c)

        for json_connection in json_connections:
            source = json_connection["src"]
            dest = json_connection["dst"]
            source_component_name = source.split(".")[0]
            source_port_name = source.split(".")[1]
            dest_component_name = dest.split(".")[0]
            dest_port_name = dest.split(".")[1]

            source_component = self.get_component(source_component_name)
            dest_componment = self.get_component(dest_component_name)
            source_component.outport(source_port_name).connect(
                dest_componment.inport(dest_port_name)
            )
