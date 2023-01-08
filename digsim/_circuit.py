# pylint: disable=invalid-name

import json

from ._component import Component
from ._waves_writer import WavesWriter


class CircuitError(Exception):
    pass


class CircuitEvent:
    def __init__(self, time_ns, port, level):
        self._time_ns = time_ns
        self._port = port
        self._level = level

    @property
    def time_ns(self):
        return self._time_ns

    @property
    def port(self):
        return self._port

    @property
    def level(self):
        return self._level

    def is_same_event(self, port):
        return port == self._port

    def update(self, time_ns, level):
        self._time_ns = time_ns
        self._level = level

    def __lt__(self, other):
        return other.time_ns > self.time_ns


class Circuit:
    def __init__(self, name=None, vcd=None):
        self._components = []
        self._circuit_events = []
        self._name = name
        self._time_ns = 0

        if vcd is not None:
            self._vcd = WavesWriter(filename=vcd)
        else:
            self._vcd = None

    @property
    def time_ns(self):
        return self._time_ns

    @property
    def components(self):
        return self._components

    def init(self):
        self._time_ns = 0
        self._circuit_events = []
        if self._vcd is not None:
            self._vcd_init()
        for comp in self._components:
            comp.init()

    def vcd(self, filename):
        if self._vcd is not None:
            raise CircuitError("VCD already started")
        self._vcd = WavesWriter(filename=filename)
        self._vcd_init()

    def vcd_close(self):
        self._vcd.close()
        self._vcd = None

    def _vcd_init(self):
        port_paths = []
        for comp in self._components:
            for port in comp.ports:
                port_paths.append((port.path, port.name))
        self._vcd.init(port_paths)

        # Dump initial state in vcd
        for comp in self._components:
            for port in comp.ports:
                self._vcd.write(port, self._time_ns)

    def _time_to_ns(self, s=None, ms=None, us=None, ns=None):
        time_ns = 0
        time_ns += s * 1e9 if s is not None else 0
        time_ns += ms * 1e6 if ms is not None else 0
        time_ns += us * 1e3 if us is not None else 0
        time_ns += ns if ns is not None else 0
        return int(time_ns)

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self._vcd.close()

    def process_single_event(self, stop_time_ns=None):
        if len(self._circuit_events) == 0:
            return False
        self._circuit_events.sort()
        if stop_time_ns is None or self._circuit_events[0].time_ns > stop_time_ns:
            return False
        event = self._circuit_events.pop(0)
        # print(f"Execute event {event.port.path}.{event.port.name} {event.time_ns}")
        self._time_ns = event.time_ns
        event.port.delta_cycle(event.level)
        if self._vcd is not None:
            self._vcd.write(event.port, self._time_ns)
        return True

    def run(self, s=None, ms=None, us=None, ns=None):
        stop_time_ns = self._time_ns + self._time_to_ns(s=s, ms=ms, us=us, ns=ns)
        while len(self._circuit_events) > 0 and self._time_ns < stop_time_ns:
            if not self.process_single_event(stop_time_ns):
                break

        self._time_ns = max(self._time_ns, stop_time_ns)

    def run_until(self, s=None, ms=None, us=None, ns=None):
        stop_time_ns = self._time_to_ns(s=s, ms=ms, us=us, ns=ns)
        if stop_time_ns > self._time_ns:
            self.run(ns=stop_time_ns - self._time_ns)

    def add_event(self, port, level, propagation_delay_ns):
        event_time_ns = self._time_ns + propagation_delay_ns
        for event in self._circuit_events:
            if event.is_same_event(port):
                event.update(event_time_ns, level)
                return
        self._circuit_events.append(CircuitEvent(event_time_ns, port, level))

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

    def connect_from_json(self, source, dest):
        source_component_name = source.split(".")[0]
        source_port_name = source.split(".")[1]
        dest_component_name = dest.split(".")[0]
        dest_port_name = dest.split(".")[1]

        source_component = self.get_component(source_component_name)
        dest_componment = self.get_component(dest_component_name)
        source_component.port(source_port_name).wire = dest_componment.port(dest_port_name)

    def from_json_file(self, filename):
        with open(filename, mode="r", encoding="utf-8") as json_file:
            json_file = json.load(json_file)

        if "circuit" not in json_file:
            raise CircuitError(f"No 'circuit' in '{filename}'")
        json_circuit = json_file["circuit"]
        if "name" not in json_circuit:
            raise CircuitError(f"No 'circuit/name' in '{filename}'")
        self._name = json_circuit["name"]
        if "components" not in json_circuit:
            raise CircuitError(f"No 'circuit/components' in '{filename}'")
        json_components = json_circuit["components"]
        if "wires" not in json_circuit:
            raise CircuitError(f"No 'circuit/connections' in '{filename}'")
        json_connections = json_circuit["wires"]

        for json_component in json_components:
            Component.from_dict(self, json_component)

        for json_connection in json_connections:
            self.connect_from_json(json_connection["src"], json_connection["dst"])

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
                "wires": connection_list,
            }
        }

        json_object = json.dumps(circuit_dict, indent=4)

        with open(filename, mode="w", encoding="utf-8") as json_file:
            json_file.write(json_object)
