# Copyright (c) Fredrik Andersson, 2023-2024
# All rights reserved

"""
Module that handles the circuit simulation of components
"""

import os

from digsim.storage_model import CircuitDataClass, CircuitFileDataClass

from ._waves_writer import WavesWriter
from .components.atoms import DigsimException


class CircuitError(DigsimException):
    """A circuit error class"""


class CircuitEvent:
    """
    The circuit event class for storing the
    delta events in the simulation.
    """

    def __init__(self, time_ns, port, value):
        self._time_ns = time_ns
        self._port = port
        self._value = value

    @property
    def time_ns(self):
        """Get the simulation time (ns) of this event"""
        return self._time_ns

    @property
    def port(self):
        """Get the port of this event"""
        return self._port

    @property
    def value(self):
        """Get the delta cycle value of this event"""
        return self._value

    def is_same_event(self, port):
        """Return True if the in the event is the same as"""
        return port == self._port

    def update(self, time_ns, value):
        """Update the event with a new time (ns) and a new value"""
        self._time_ns = time_ns
        self._value = value

    def __lt__(self, other):
        return other.time_ns > self.time_ns


class Circuit:
    """Class thay handles the circuit simulation"""

    def __init__(self, name=None, vcd=None):
        self._components = {}
        self._circuit_events = []
        self._name = name
        self._time_ns = 0
        self._folder = None

        if vcd is not None:
            self._vcd = WavesWriter(filename=vcd)
        else:
            self._vcd = None

    @property
    def name(self):
        """Get the circuit name"""
        return self._name

    @property
    def time_ns(self):
        """Get the current simulation time (ns)"""
        return self._time_ns

    @property
    def components(self):
        """Get the components in this circuit"""
        comp_array = []
        for _, comp in self._components.items():
            comp_array.append(comp)
        return comp_array

    def load_path(self, path):
        """Get the load path relative to the circuit path"""
        if self._folder is not None:
            return self._folder + "/" + path
        return path

    def store_path(self, path):
        """Get the store path relative to the circuit path"""
        if self._folder is not None:
            return os.path.relpath(path, self._folder)
        return path

    def delete_component(self, component):
        """Delete a component from the circuit"""
        del self._components[component.name()]
        component.remove_connections()

    def get_toplevel_components(self):
        """Get toplevel components in the circuit"""
        toplevel_components = []
        for _, comp in self._components.items():
            if comp.is_toplevel():
                toplevel_components.append(comp)
        return toplevel_components

    def init(self):
        """Initialize circuit and components (and ports)"""
        self._time_ns = 0
        self._circuit_events = []
        if self._vcd is not None:
            self._vcd_init()
        for _, comp in self._components.items():
            comp.init()
        for _, comp in self._components.items():
            comp.default_state()
        self.run_until(ns=0)  # Handle all time zero events

    def clear(self):
        """Remove all components"""
        for _, comp in self._components.items():
            comp.clear()
        self._components = {}

    def vcd(self, filename):
        """Start wave collecting in a gtkwave .vcd file"""
        if self._vcd is not None:
            raise CircuitError("VCD already started")
        self._vcd = WavesWriter(filename=filename)
        self._vcd_init()

    def vcd_close(self):
        """Close gtkwave .vcd file"""
        if self._vcd is not None:
            self._vcd.close()
            self._vcd = None

    def _vcd_init(self):
        port_info = []
        for _, comp in self._components.items():
            for port in comp.ports:
                port_info.append((port.path(), port.name(), port.width))
        self._vcd.init(port_info)

        # Dump initial state in vcd
        for _, comp in self._components.items():
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
        """
        Process one simulation event
        Return False if ther are now events of if the stop_time has passed
        """
        if len(self._circuit_events) == 0:
            return False, False
        self._circuit_events.sort()
        if stop_time_ns is None or self._circuit_events[0].time_ns > stop_time_ns:
            return False, False
        event = self._circuit_events.pop(0)
        # print(
        #     f"Execute event {event.port.path()}.{event.port.name()}"
        #     " {event.time_ns} {event.value}"
        # )
        self._time_ns = event.time_ns
        event.port.delta_cycle(event.value)
        toplevel = event.port.parent().is_toplevel()
        if self._vcd is not None:
            self._vcd.write(event.port, self._time_ns)
        return True, toplevel

    def _is_toplevel_event(self):
        if len(self._circuit_events) == 0:
            return False
        event = self._circuit_events[0]
        return event.port.parent().is_toplevel()

    def run(self, s=None, ms=None, us=None, ns=None, single_step=False):
        """Run simulation for a period of time"""
        stop_time_ns = self._time_ns + self._time_to_ns(s=s, ms=ms, us=us, ns=ns)
        single_step_stop = False
        while len(self._circuit_events) > 0 and self._time_ns <= stop_time_ns:
            more_events, top_level_event = self.process_single_event(stop_time_ns)
            if not more_events:
                break
            if single_step and top_level_event:
                stop_time_ns = self._time_ns
                single_step_stop = True
        self._time_ns = max(self._time_ns, stop_time_ns)
        return single_step_stop

    def run_until(self, s=None, ms=None, us=None, ns=None):
        """Run simulation until a specified time"""
        stop_time_ns = self._time_to_ns(s=s, ms=ms, us=us, ns=ns)
        if stop_time_ns >= self._time_ns:
            self.run(ns=stop_time_ns - self._time_ns)

    def add_event(self, port, value, propagation_delay_ns):
        """Add delta cycle event, this will also write values to .vcd file"""
        event_time_ns = self._time_ns + propagation_delay_ns
        # print(f"Add event {port.parent().name()}:{port.name()} => {value}")
        for event in self._circuit_events:
            if event.is_same_event(port):
                event.update(event_time_ns, value)
                return
        self._circuit_events.append(CircuitEvent(event_time_ns, port, value))

    def add_component(self, component):
        """Add component to circuit"""
        name_id = 1
        namebase = component.name()
        while component.name() in self._components:
            component.set_name(f"{namebase}_{name_id}", update_circuit=False)
            name_id += 1
        self._components[component.name()] = component

    def change_component_name(self, component, name):
        """Change component name"""
        comp = self._components[component.name()]
        del self._components[component.name()]
        comp.set_name(name, update_circuit=False)
        self.add_component(comp)

    def get_component(self, component_name):
        """Get component witgh 'component_name'"""
        comp = self._components.get(component_name)
        if comp is not None:
            return comp
        raise CircuitError(f"Component '{component_name}' not found")

    def to_dataclass(self, folder=None):
        """Generate dict from circuit, used when storing circuit"""
        if self._name is None:
            raise CircuitError("Circuit must have a name")
        self._folder = folder
        return CircuitDataClass.from_circuit(self)

    def from_dataclass(
        self, circuit_dc, folder=None, component_exceptions=True, connect_exceptions=True
    ):
        """Clear circuit and add components from dict"""
        self._folder = folder
        self.clear()

        exception_str_list = []
        for component in circuit_dc.components:
            try:
                component.create(self)
            except DigsimException as exc:
                if component_exceptions:
                    raise exc
                exception_str_list.append(f"{str(exc.__class__.__name__)}:{str(exc)}")
            except FileNotFoundError as exc:
                if component_exceptions:
                    raise exc
                exception_str_list.append(f"{str(exc.__class__.__name__)}:{str(exc)}")
        for wire in circuit_dc.wires:
            try:
                wire.connect(self)
            except DigsimException as exc:
                if connect_exceptions:
                    raise exc
                exception_str_list.append(f"{exc.__class__.__name__}:{str(exc)}")

        return exception_str_list

    def to_json_file(self, filename):
        """Store circuit in json file"""
        circuitfile_dc = CircuitFileDataClass(circuit=self.to_dataclass())
        circuitfile_dc.save(filename)

    def from_json_file(self, filename, folder=None):
        """Load circuit from json file"""
        file_dc = CircuitFileDataClass.load(filename)
        self.from_dataclass(file_dc.circuit, folder)
