import json

from vcd import VCDWriter

from components import Component


class CircuitError(Exception):
    pass


class CircuitEvent:
    def __init__(self, port, time_ns):
        self._time_ns = time_ns
        self._port = port

    @property
    def time_ns(self):
        return self._time_ns

    @property
    def port(self):
        return self._port

    def __lt__(self, other):
        return other.time_ns < self.time_ns


class Circuit:
    def __init__(self, name=None, vcd=None):
        self._components = []
        self._circuit_events = []
        self._name = name
        self._vcd_file = None
        self._vcd_writer = None
        self._vcd_dict = {}
        self._time_ns = 0
        self._vcd_name = vcd

    @property
    def time_ns(self):
        return self._time_ns

    def init(self):
        self.vcd()
        for comp in self._components:
            comp.init()

    def vcd(self, vcd=None):
        if vcd is not None and self._vcd_name is not None:
            raise CircuitError("VCD already started")

        if vcd is not None:
            self._vcd_name = vcd

        if self._vcd_name is not None:
            self._vcd_file = open(self._vcd_name, mode="w")
            self._vcd_writer = VCDWriter(self._vcd_file, timescale="1 ns", date="today")
            for port_path, port_name in self.get_port_paths():
                var = self._vcd_writer.register_var(
                    port_path, port_name, "integer", size=1
                )
                self._vcd_dict[f"{port_path}.{port_name}"] = var

    def vcd_close(self):
        if self._vcd_writer is not None:
            self._vcd_writer.close()
            self._vcd_writer = None

        if self._vcd_file is not None:
            self._vcd_file.close()
            self._vcd_file = None

        self._vcd_name = None

    def _time_to_ns(self, s=None, ms=None, us=None, ns=None):
        time_ns = 0
        time_ns += s * 1e9 if s is not None else 0
        time_ns += ms * 1e6 if ms is not None else 0
        time_ns += us * 1e3 if us is not None else 0
        time_ns += ns if ns is not None else 0
        return int(time_ns)

    def __exit__(self):
        self.vcd_close()

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

    def process_single_event(self, stop_time_ns=None):
        if len(self._circuit_events) == 0:
            return False
        self._circuit_events.sort()
        if stop_time_ns is None or self._circuit_events[0].time_ns > stop_time_ns:
            return False
        event = self._circuit_events.pop()
        # print(f"Execute event {event.port.path}.{event.port.name} {event.time_ns}")
        self._time_ns = event.time_ns
        event.port.delta_cycle()
        if self._vcd_writer is not None:
            self.vcd_dump(event.port)
        return True

    def run(self, s=None, ms=None, us=None, ns=None):
        recursion = 0
        stop_time_ns = self._time_ns + self._time_to_ns(s=s, ms=ms, us=us, ns=ns)

        while len(self._circuit_events) > 0 and self._time_ns < stop_time_ns:
            if not self.process_single_event(stop_time_ns):
                break

        if self._time_ns < stop_time_ns:
            self._time_ns = stop_time_ns

    def run_until(self, s=None, ms=None, us=None, ns=None):
        stop_time_ns = self._time_to_ns(s=s, ms=ms, us=us, ns=ns)
        if stop_time_ns > self._time_ns:
            self.run(ns=stop_time_ns - self._time_ns)

    def add_event(self, port):
        self._circuit_events.append(
            CircuitEvent(port, self._time_ns + port.propagation_delay_ns)
        )

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
        with open(filename, mode="r") as f:
            json_file = json.load(f)

        if "circuit" not in json_file:
            raise CircuitError(f"No 'circuit' in '{filename}'")
        json_circuit = json_file["circuit"]
        if "name" not in json_circuit:
            raise CircuitError(f"No 'circuit/name' in '{filename}'")
        self._name = json_circuit["name"]
        if "components" not in json_circuit:
            raise CircuitError(f"No 'circuit/components' in '{filename}'")
        json_components = json_circuit["components"]
        if "connections" not in json_circuit:
            raise CircuitError(f"No 'circuit/connections' in '{filename}'")
        json_connections = json_circuit["connections"]

        for json_component in json_components:
            c = Component.from_dict(self, json_component)

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

    def to_json_file(self, filename):
        if self._name is None:
            raise CircuitError("Circuit must have a name")

        components_list = []
        for comp in self._components:
            components_list.append(comp.to_dict())

        connection_list = []
        for comp in self._components:
            for port in comp.ports:
                port_conn_list = port.to_dict_list()
                connection_list.extend(port_conn_list)

        circuit_dict = {
            "circuit": {
                "name": self._name,
                "components": components_list,
                "connections": connection_list,
            }
        }

        json_object = json.dumps(circuit_dict, indent=4)

        with open(filename, mode="w") as f:
            f.write(json_object)
