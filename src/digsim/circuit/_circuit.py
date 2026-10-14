# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""
Module that handles the circuit simulation of components
"""

from __future__ import annotations

import heapq
import os
from pathlib import Path
from types import TracebackType
from typing import TYPE_CHECKING

from digsim.storage_model import CircuitDataClass, CircuitFileDataClass

from ._waves_writer import WavesWriter
from .components.atoms import (
    VALUE_TYPE,
    Component,
    DigsimException,
    PortMultiBitWire,
    PortOutDelta,
)


if TYPE_CHECKING:
    from typing_extensions import Self

EventPort = PortOutDelta | PortMultiBitWire


class CircuitError(DigsimException):
    """A circuit error class"""


class CircuitEvent:
    """
    The circuit event class for storing the
    delta events in the simulation.
    """

    __slots__ = ("_port", "_time_ns", "_value")

    def __init__(self, time_ns: int, port: EventPort, value: VALUE_TYPE) -> None:
        self._time_ns: int = time_ns
        self._port: EventPort = port
        self._value: VALUE_TYPE = value

    def __lt__(self, other: CircuitEvent) -> bool:
        # Called for every comparison in the event queue, so read the attributes directly
        return self._time_ns < other._time_ns

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, CircuitEvent)
            and self._port == other._port
            and self._time_ns == other._time_ns
            and self._value == other._value
        )


class Circuit:
    """Class thay handles the circuit simulation"""

    def __init__(self, name: str | None = None, vcd: str | None = None) -> None:
        self._components: dict[str, Component] = {}
        self._circuit_events: list[CircuitEvent] = []
        self._events_by_port: dict[EventPort, CircuitEvent] = {}
        self._name: str | None = name
        self._time_ns: int = 0
        self._folder: str = "."
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

    def load_path(self, path: str | Path) -> str:
        """Get the load path relative to the circuit path"""
        load_path = Path(path)
        if not load_path.is_absolute():
            load_path = Path(self._folder) / load_path
        return str(load_path)

    def store_path(self, path: str | Path) -> str:
        """Get the store path relative to the circuit path"""

        store_path = Path(path).resolve(strict=False)
        folder_path = Path(self._folder).resolve(strict=False)
        try:
            store_path = Path(os.path.relpath(store_path, folder_path))
        except ValueError:
            pass  # No relative path (another drive on Windows), keep the absolute path
        return str(store_path)

    def delete_component(self, component: Component) -> None:
        """Delete a component, and the components it is built from, from the circuit"""
        for comp in list(self._components.values()):
            part: Component | None = comp
            while part is not None and part is not component:
                part = part.parent
            if part is component:
                del self._components[comp.name()]
        component.remove_connections()

    def get_toplevel_components(self) -> list[Component]:
        """Get toplevel components in the circuit"""
        return [comp for comp in self._components.values() if comp.is_toplevel()]

    def init(self) -> None:
        """Initialize circuit and components (and ports)"""
        self._time_ns = 0
        self._circuit_events = []
        self._events_by_port = {}
        if self._vcd is not None:
            self._vcd_init()
        for comp in self._components.values():
            comp.init()
        for comp in self._components.values():
            comp.default_state()
        self.run_until(ns=0)  # Handle all time zero events

    def clear(self) -> None:
        """Remove all components"""
        for comp in self._components.values():
            comp.clear()
        self._components = {}

    def vcd(self, filename: str) -> None:
        """Start wave collecting in a gtkwave .vcd file"""
        if self._vcd is not None:
            raise CircuitError("VCD already started")
        self._vcd = WavesWriter(filename=filename)
        self._vcd_init()

    def vcd_close(self) -> None:
        """Close gtkwave .vcd file"""
        if self._vcd is not None:
            self._vcd.close()
            self._vcd = None

    def _vcd_init(self) -> None:
        if self._vcd is None:
            return
        ports = []
        for comp in self._components.values():
            ports.extend(comp.ports)
        self._vcd.init(ports)

        # Dump initial state in vcd
        for comp in self._components.values():
            for port in comp.ports:
                self._vcd.write(port, self._time_ns)

    def _time_to_ns(
        self,
        s: float | None = None,
        ms: float | None = None,
        us: float | None = None,
        ns: float | None = None,
    ) -> int:
        time_ns: float = 0
        time_ns += s * 1e9 if s is not None else 0
        time_ns += ms * 1e6 if ms is not None else 0
        time_ns += us * 1e3 if us is not None else 0
        time_ns += ns if ns is not None else 0
        return int(time_ns)

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        exc_traceback: TracebackType | None,
    ) -> None:
        self.vcd_close()

    def process_single_event(self, stop_time_ns: int | None = None) -> tuple[bool, bool]:
        """
        Process one simulation event
        Return False if there are no events or if the stop_time has passed
        """
        events = self._circuit_events
        events_by_port = self._events_by_port
        while events:
            event = heapq.heappop(events)
            port = event._port
            latest = events_by_port.get(port)
            if latest is not event and latest != event:
                # A stale event, a later event for the same port replaced it
                continue
            if stop_time_ns is not None and event._time_ns > stop_time_ns:
                # Put the event back if it's after the stop time
                heapq.heappush(events, event)
                return False, False
            del events_by_port[port]
            self._time_ns = event._time_ns
            port.delta_cycle(event._value)
            if self._vcd is not None:
                self._vcd.write(port, self._time_ns)
            return True, port.parent().is_toplevel()
        return False, False

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
        # The loop in process_single_event(), inlined since it runs for every event
        events = self._circuit_events
        events_by_port = self._events_by_port
        heappop = heapq.heappop
        vcd = self._vcd
        while events and self._time_ns <= stop_time_ns:
            event = heappop(events)
            port = event._port
            latest = events_by_port.get(port)
            if latest is not event and latest != event:
                # A stale event, a later event for the same port replaced it
                continue
            time_ns = event._time_ns
            if time_ns > stop_time_ns:
                # Put the event back if it's after the stop time
                heapq.heappush(events, event)
                break
            del events_by_port[port]
            self._time_ns = time_ns
            port.delta_cycle(event._value)
            if vcd is not None:
                vcd.write(port, time_ns)
            if single_step and port.parent().is_toplevel():
                # Finish the events at this time, then stop
                stop_time_ns = time_ns
                single_step_stop = True
        self._time_ns = max(self._time_ns, stop_time_ns)
        if vcd is not None:
            vcd.flush()
        return single_step_stop

    def run_until(
        self,
        s: int | None = None,
        ms: int | None = None,
        us: int | None = None,
        ns: int | None = None,
    ) -> None:
        """Run simulation until a specified time"""
        stop_time_ns = self._time_to_ns(s=s, ms=ms, us=us, ns=ns)
        if stop_time_ns >= self._time_ns:
            self.run(ns=stop_time_ns - self._time_ns)

    def add_event(self, port: EventPort, value: VALUE_TYPE, propagation_delay_ns: int) -> None:
        """Add delta cycle event, this will also write values to .vcd file"""
        event_time_ns = self._time_ns + propagation_delay_ns
        # print(f"Add event {port.parent().name()}:{port.name()} => {value}")
        event = CircuitEvent(event_time_ns, port, value)
        self._events_by_port[port] = event
        heapq.heappush(self._circuit_events, event)

    def add_component(self, component: Component) -> None:
        """Add component to circuit"""
        name_id = 1
        namebase = component.name()
        while component.name() in self._components:
            component.set_name(f"{namebase}_{name_id}", update_circuit=False)
            name_id += 1
        self._components[component.name()] = component

    def change_component_name(self, component: Component, name: str) -> None:
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

    def to_dataclass(self, folder: str = ".") -> CircuitDataClass:
        """Generate dict from circuit, used when storing circuit"""
        if self._name is None:
            raise CircuitError("Circuit must have a name")
        self._folder = folder
        return CircuitDataClass.from_circuit(self)

    def from_dataclass(
        self,
        circuit_dc: CircuitDataClass,
        folder: str = "",
        component_exceptions: bool = True,
        connect_exceptions: bool = True,
    ) -> list[str]:
        """Clear circuit and add components from dict"""
        self._folder = folder
        self.clear()

        exception_str_list = []
        for component in circuit_dc.components:
            names_before = set(self._components)
            try:
                component.create(self)
            except (DigsimException, FileNotFoundError) as exc:
                # Remove what the failed component added before it failed
                for name in set(self._components) - names_before:
                    del self._components[name]
                if component_exceptions:
                    raise
                exception_str_list.append(f"{exc.__class__.__name__}:{exc!s}")
        for wire in circuit_dc.wires:
            try:
                wire.connect(self)
            except DigsimException as exc:
                if connect_exceptions:
                    raise
                exception_str_list.append(f"{exc.__class__.__name__}:{exc!s}")

        return exception_str_list

    def to_json_file(self, filename: str) -> None:
        """Store circuit in json file"""
        circuitfile_dc = CircuitFileDataClass(circuit=self.to_dataclass())
        circuitfile_dc.save(filename)

    def from_json_file(self, filename: str, folder: str = ".") -> None:
        """Load circuit from json file"""
        file_dc = CircuitFileDataClass.load(filename)
        self.from_dataclass(file_dc.circuit, folder)
