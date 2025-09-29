# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""
Module that handles the circuit simulation of components
"""

from __future__ import annotations

import heapq
import pathlib
from typing import Tuple

from digsim.storage_model import CircuitDataClass, CircuitFileDataClass

from ._waves_writer import WavesWriter
from .components.atoms import VALUE_TYPE, Component, DigsimException, PortOutDelta


class CircuitError(DigsimException):
    """A circuit error class"""


class CircuitEvent:
    """
    The circuit event class for storing the
    delta events in the simulation.
    """

    def __init__(self, time_ns: int, port: PortOutDelta, value: VALUE_TYPE):
        self._time_ns: int = time_ns
        self._port: PortOutDelta = port
        self._value: VALUE_TYPE = value

    @property
    def time_ns(self) -> int:
        """Get the simulation time (ns) of this event"""
        return self._time_ns

    @property
    def port(self) -> PortOutDelta:
        """Get the port of this event"""
        return self._port

    @property
    def value(self) -> VALUE_TYPE:
        """Get the delta cycle value of this event"""
        return self._value

    def is_same_event(self, port: PortOutDelta):
        """Return True if the in the event is the same as"""
        return port == self._port

    def update(self, time_ns: int, value: VALUE_TYPE):
        """Update the event with a new time (ns) and a new value"""
        self._time_ns = time_ns
        self._value = value

    def __lt__(self, other) -> bool:
        return other.time_ns > self.time_ns

    def __eq__(self, other) -> bool:
        return (
            isinstance(other, CircuitEvent)
            and self._port == other._port
            and self._time_ns == other._time_ns
            and self._value == other._value
        )


class Circuit:
    """Class thay handles the circuit simulation"""

    def __init__(self, name: str | None = None, vcd: str | None = None):
        self._components: dict[str, Component] = {}
        self._circuit_events: list[CircuitEvent] = []
        self._events_by_port: dict[PortOutDelta, CircuitEvent] = {}
        self._name: str | None = name
        self._time_ns: int = 0
        self._folder: str | None = None
        self._vcd: WavesWriter | None = None

        if vcd is not None:
            self._vcd = WavesWriter(filename=vcd)

    @property
    def name(self) -> str | None:
        """Get the circuit name"""
        return self._name

    @property
    def time_ns(self) -> int:
        """Get the current simulation time (ns)"""
        return self._time_ns

    @property
    def components(self) -> list[Component]:
        """Get the components in this circuit"""
        return list(self._components.values())

    def load_path(self, path) -> str:
        """Get the load path relative to the circuit path"""
        if self._folder is not None:
            return self._folder + "/" + path
        return path

    def store_path(self, path) -> str:
        """Get the store path relative to the circuit path"""
        if self._folder is not None:
            return str(
                pathlib.Path(path).resolve().absolute().relative_to(pathlib.Path(self._folder))
            )
        return path

    def delete_component(self, component: Component):
        """Delete a component from the circuit"""
        del self._components[component.name()]
        component.remove_connections()

    def get_toplevel_components(self) -> list[Component]:
        """Get toplevel components in the circuit"""
        return [comp for comp in self._components.values() if comp.is_toplevel()]

    def init(self):
        """Initialize circuit and components (and ports)"""
        self._time_ns = 0
        self._circuit_events = []
        self._events_by_port = {}
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

    def _time_to_ns(self, s=None, ms=None, us=None, ns=None) -> int:
        time_ns = 0
        time_ns += s * 1e9 if s is not None else 0
        time_ns += ms * 1e6 if ms is not None else 0
        time_ns += us * 1e3 if us is not None else 0
        time_ns += ns if ns is not None else 0
        return int(time_ns)

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self._vcd.close()

    def process_single_event(self, stop_time_ns=None) -> Tuple[bool, bool]:
        """
        Process one simulation event
        Return False if ther are now events of if the stop_time has passed
        """
        while self._circuit_events:
            event = heapq.heappop(self._circuit_events)

            # Check if this is the latest event for this port
            if event != self._events_by_port.get(event.port):
                # This is a stale event, ignore it
                continue

            if stop_time_ns is not None and event.time_ns > stop_time_ns:
                # Put the event back if it's after the stop time
                heapq.heappush(self._circuit_events, event)
                return False, False

            del self._events_by_port[event.port]
            # print(
            #     f"Execute event {event.port.path()}.{event.port.name()}"
            #     f" {event.time_ns} {event.value}"
            # )
            self._time_ns = event.time_ns
            event.port.delta_cycle(event.value)
            toplevel = event.port.parent().is_toplevel()
            if self._vcd is not None:
                self._vcd.write(event.port, self._time_ns)
            return True, toplevel

        return False, False

    def _is_toplevel_event(self) -> bool:
        if len(self._circuit_events) == 0:
            return False
        event = self._circuit_events[0]
        return event.port.parent().is_toplevel()

    def run(
        self,
        s: int | None = None,
        ms: int | None = None,
        us: int | None = None,
        ns: int | None = None,
        single_step: bool = False,
    ) -> bool:
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

    def run_until(
        self,
        s: int | None = None,
        ms: int | None = None,
        us: int | None = None,
        ns: int | None = None,
    ):
        """Run simulation until a specified time"""
        stop_time_ns = self._time_to_ns(s=s, ms=ms, us=us, ns=ns)
        if stop_time_ns >= self._time_ns:
            self.run(ns=stop_time_ns - self._time_ns)

    def add_event(self, port: PortOutDelta, value: VALUE_TYPE, propagation_delay_ns: int):
        """Add delta cycle event, this will also write values to .vcd file"""
        event_time_ns = self._time_ns + propagation_delay_ns
        # print(f"Add event {port.parent().name()}:{port.name()} => {value}")
        event = CircuitEvent(event_time_ns, port, value)
        self._events_by_port[port] = event
        heapq.heappush(self._circuit_events, event)

    def add_component(self, component: Component):
        """Add component to circuit"""
        name_id = 1
        namebase = component.name()
        while component.name() in self._components:
            component.set_name(f"{namebase}_{name_id}", update_circuit=False)
            name_id += 1
        self._components[component.name()] = component

    def change_component_name(self, component: Component, name: str):
        """Change component name"""
        comp = self._components[component.name()]
        del self._components[component.name()]
        comp.set_name(name, update_circuit=False)
        self.add_component(comp)

    def get_component(self, component_name: str) -> Component:
        """Get component witgh 'component_name'"""
        comp = self._components.get(component_name)
        if comp is not None:
            return comp
        raise CircuitError(f"Component '{component_name}' not found")

    def to_dataclass(self, folder: str | None = None) -> CircuitDataClass:
        """Generate dict from circuit, used when storing circuit"""
        if self._name is None:
            raise CircuitError("Circuit must have a name")
        self._folder = folder
        return CircuitDataClass.from_circuit(self)

    def from_dataclass(
        self,
        circuit_dc: CircuitDataClass,
        folder: str | None = None,
        component_exceptions: bool = True,
        connect_exceptions: bool = True,
    ) -> list[str]:
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

    def to_json_file(self, filename: str):
        """Store circuit in json file"""
        circuitfile_dc = CircuitFileDataClass(circuit=self.to_dataclass())
        circuitfile_dc.save(filename)

    def from_json_file(self, filename: str, folder: str | None = None):
        """Load circuit from json file"""
        file_dc = CircuitFileDataClass.load(filename)
        self.from_dataclass(file_dc.circuit, folder)
