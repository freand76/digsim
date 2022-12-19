import json

from vcd import VCDWriter

from components import ActorComponent, Component


class CircuitError(Exception):
    pass


class Circuit:
    def __init__(self, vcd=None):
        self._components = []
        self._delta_cycle_ports = []
        self._vcd_name = vcd
        self._vcd_file = None
        self._vcd_writer = None
        self._vcd_dict = {}
        self._time_ns = 0

    def init(self):
        if self._vcd_name is not None:
            self._vcd_file = open(self._vcd_name, mode="w")
            self._vcd_writer = VCDWriter(self._vcd_file, timescale="1 ns", date="today")
            for port_path, port_name in self.get_port_paths():
                full_name = f"{port_path}.{port_name}".replace(".", "_")
                var = self._vcd_writer.register_var(
                    port_path, full_name, "integer", size=1
                )
                self._vcd_dict[f"{port_path}.{port_name}"] = var

        for comp in self._components:
            comp.init()

    def close(self):
        if self._vcd_writer is not None:
            self._vcd_writer.close()
            self._vcd_writer = None

        if self._vcd_file is not None:
            self._vcd_file.close()
            self._vcd_file = None

    def time_increase(self, s=None, ms=None, us=None, ns=None):
        self._time_ns += s * 1e9 if s is not None else 0
        self._time_ns += ms * 1e6 if ms is not None else 0
        self._time_ns += us * 1e3 if us is not None else 0
        self._time_ns += ns if ns is not None else 0

    def __exit__(self):
        self.close()

    def get_port_paths(self):
        port_paths = []
        for comp in self._components:
            for port in comp.ports:
                port_paths.append((port.path, port.name))
        return port_paths

    def vcd_dump(self, port):
        var = self._vcd_dict[f"{port.path}.{port.name}"]
        self._vcd_writer.change(var, timestamp=self._time_ns, value=port.intval)
        for p in port.destinations:
            self.vcd_dump(p)

    def delta_cycle(self):
        while len(self._delta_cycle_ports) > 0:
            ports = self._delta_cycle_ports
            self._delta_cycle_ports = []
            for port in ports:
                # print(f" - Delta {port.parent}")
                port.delta_cycle()
                if self._vcd_writer is not None:
                    self.vcd_dump(port)

    def delta_cycle_needed(self, port):
        self._delta_cycle_ports.append(port)

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
            c = Component.from_json(self, json_component)

        for json_connection in json_connections:
            source = json_connection["src"]
            dest = json_connection["dst"]
            source_component_name = source.split(".")[0]
            source_port_name = source.split(".")[1]
            dest_component_name = dest.split(".")[0]
            dest_port_name = dest.split(".")[1]

            source_component = self.get_component(source_component_name)
            dest_componment = self.get_component(dest_component_name)
            source_component.port(source_port_name).connect(
                dest_componment.port(dest_port_name)
            )
