# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""
Module that handles the circuit simulation of components
"""

from __future__ import annotations

import heapq
import os
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path, PureWindowsPath
from types import TracebackType
from typing import TYPE_CHECKING, NamedTuple, Self

from digsim.storage_model import CircuitDataClass, CircuitFileDataClass

from ._waves_writer import WavesWriter
from .components.atoms import (
    VALUE_TYPE,
    Component,
    DigsimException,
    Port,
    PortInOut,
    PortMultiBitWire,
    PortOutDelta,
)


if TYPE_CHECKING:
    from .components._circuit_port import CircuitPort


EventPort = PortOutDelta | PortMultiBitWire | PortInOut


class CircuitError(DigsimException):
    """A circuit error class"""


class RunResult(NamedTuple):
    """
    How a run with a time limit ended (see Circuit.run_within()): if it stopped for a
    single step, and if it ran all the time it was asked to
    """

    single_step: bool
    complete: bool


# The slices of simulated time that run_within() runs, between its looks at the clock: it
# starts small, so that a circuit that oscillates gets a look soon, and grows while the
# slices are fast, to at most MAX_SLICE_NS
START_SLICE_NS = 1_000
MAX_SLICE_NS = 1_000_000


class CircuitEvent(float):
    """
    The circuit event class for storing the
    delta events in the simulation.

    An event is its time as a float, so that the event queue compares events in C
    instead of calling a Python __lt__ for every comparison. The comparisons give the
    same results, so events at the same time keep their order.
    """

    __slots__ = ("_port", "_time_ns", "_value")

    _port: EventPort
    _time_ns: int
    _value: VALUE_TYPE


class Circuit:
    """
    A circuit: holds the components and runs the simulation. Use it in a with statement,
    `with Circuit(vcd="waves.vcd") as circuit:`, to close the VCD file at the end.

    Args:
        name: The circuit name, needed to save the circuit.
        vcd: A VCD file to write waveforms to, from init().
    """

    def __init__(self, name: str | None = None, vcd: str | None = None) -> None:
        self._components: dict[str, Component] = {}
        self._circuit_events: list[CircuitEvent] = []
        self._events_by_port: dict[EventPort, CircuitEvent] = {}
        self._name: str | None = name
        self._time_ns: int = 0
        self._folder: str = "."
        self._vcd: WavesWriter | None = None
        # The slice of run_within()
        self._slice_ns = START_SLICE_NS

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
        """Get the load path relative to the circuit path, empty for no path"""
        if not str(path):
            return ""
        if "\\" in str(path):
            # Stored with backslashes on Windows by an older version, read on all systems
            path = PureWindowsPath(path).as_posix()
        load_path = Path(path)
        if not load_path.is_absolute():
            load_path = Path(self._folder) / load_path
        return str(load_path)

    def store_path(self, path: str | Path) -> str:
        """Get the store path relative to the circuit path, empty for no path"""
        if not str(path):
            return ""
        store_path = Path(path).resolve(strict=False)
        folder_path = Path(self._folder).resolve(strict=False)
        try:
            store_path = Path(os.path.relpath(store_path, folder_path))
        except ValueError:
            pass  # No relative path (another drive on Windows), keep the absolute path
        # '/' also on Windows, so that the circuit file can be loaded on all systems
        return store_path.as_posix()

    @contextmanager
    def adding_components(self) -> Iterator[None]:
        """
        Context for creating components: if the block raises an exception, the components
        it added to the circuit before failing are removed again
        """
        names_before = set(self._components)
        try:
            yield
        except BaseException:
            for name in set(self._components) - names_before:
                del self._components[name]
            raise

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

    def ports(self) -> list[CircuitPort]:
        """
        The circuit ports of the circuit (CircuitInput, CircuitOutput and CircuitInOut), its
        interface when it is used as a subcircuit, in the order they were added
        """
        # Imported here: the components import the circuit
        from digsim.circuit.components._circuit_port import circuit_ports

        return circuit_ports(self)

    def init(self) -> None:
        """
        Initialize the circuit: set the time to 0 and all ports to "X", then let the
        components set their default state. Call it after adding and connecting components.
        """
        self._time_ns = 0
        self._circuit_events = []
        self._events_by_port = {}
        self._slice_ns = START_SLICE_NS
        if self._vcd is not None:
            self._vcd_init()
        for comp in self._components.values():
            comp.init()
        for comp in self._components.values():
            comp.default_state()
        self.run_until(ns=0)  # Handle all time zero events

    def clear(self) -> None:
        """Remove all components, and the events of their ports"""
        for comp in self._components.values():
            comp.clear()
        self._components = {}
        self._circuit_events = []
        self._events_by_port = {}

    def vcd(self, filename: str) -> None:
        """
        Start writing waveforms to a VCD file, for GTKWave or another viewer.

        Raises:
            CircuitError: If a VCD file is already open.
            OSError: If the file can't be opened.
        """
        if self._vcd is not None:
            raise CircuitError("VCD already started")
        self._vcd = WavesWriter(filename=filename)
        try:
            self._vcd_init()
        except BaseException:
            # The file could not be opened, don't keep a writer without a file
            self._vcd = None
            raise

    def vcd_close(self) -> None:
        """Finish and close the VCD file, if one is open"""
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
        # Rounded, since a time like 1.001 µs is 1000.9999999999999 ns as a float
        return round(time_ns)

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
        Process only the next event, to step through a simulation.

        Args:
            stop_time_ns: Don't process an event after this time, keep it for later.

        Returns:
            If an event was processed (False if there were none, or the next one is after
            stop_time_ns), and if it was on a port of a top-level component, rather than
            inside one like a Yosys component.
        """
        events = self._circuit_events
        events_by_port = self._events_by_port
        while events:
            event = heapq.heappop(events)
            port = event._port
            latest = events_by_port.get(port)
            if latest is not event and (
                latest is None
                or latest._time_ns != event._time_ns
                or latest._value != event._value
            ):
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
        s: float | None = None,
        ms: float | None = None,
        us: float | None = None,
        ns: float | None = None,
        single_step: bool = False,
    ) -> bool:
        """
        Run the simulation for a period of time. The times are added together, so
        run(ms=1, us=500) runs for 1.5 ms.

        Args:
            s: Seconds.
            ms: Milliseconds.
            us: Microseconds.
            ns: Nanoseconds.
            single_step: Stop after the first event on a port of a top-level component,
                at the end of its time (the GUI's Single Step).

        Returns:
            True if the run stopped for a single step.
        """
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
            if latest is not event and (
                latest is None
                or latest._time_ns != event._time_ns
                or latest._value != event._value
            ):
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

    def run_within(
        self,
        seconds: float,
        s: float | None = None,
        ms: float | None = None,
        us: float | None = None,
        ns: float | None = None,
        single_step: bool = False,
    ) -> RunResult:
        """
        Run the simulation like run(), but for at most a time on the clock: a circuit that
        oscillates makes so many events that a run could take minutes. It runs slices of
        the time with run(), and stops after the slice that takes it past the limit. The
        events are the same as with one run(), only where it stops can be earlier.

        Args:
            seconds: The most time on the clock it runs (a slice can take more).
            s: Seconds of simulated time.
            ms: Milliseconds.
            us: Microseconds.
            ns: Nanoseconds.
            single_step: Stop after the first event on a port of a top-level component,
                like run().

        Returns:
            If it stopped for a single step, and if it ran all the time.
        """
        stop_time_ns = self.time_ns + self._time_to_ns(s=s, ms=ms, us=us, ns=ns)
        deadline = time.perf_counter() + seconds
        while self.time_ns < stop_time_ns:
            start = time.perf_counter()
            step_ns = min(self._slice_ns, stop_time_ns - self.time_ns)
            if self.run(ns=step_ns, single_step=single_step):
                return RunResult(single_step=True, complete=True)
            now = time.perf_counter()
            # Longer slices while they are fast, shorter when they are slow
            if now - start < seconds / 20:
                self._slice_ns = min(MAX_SLICE_NS, self._slice_ns * 2)
            elif now - start > seconds / 5:
                self._slice_ns = max(1, self._slice_ns // 2)
            if now >= deadline and self.time_ns < stop_time_ns:
                return RunResult(single_step=False, complete=False)
        return RunResult(single_step=False, complete=True)

    def restart_slices(self) -> None:
        """
        Start run_within() with a short slice again, like after an input changed: it can
        start an oscillation, which a long slice would run for long
        """
        self._slice_ns = START_SLICE_NS

    def oscillating_ports(self, ns: int = 200, changes: int = 10) -> list[Port]:
        """
        The ports of the top-level components that oscillate: it runs the simulation for a
        while, a nanosecond at a time, and counts how often each output changes. A port
        that changes at least 'changes' times in 'ns' nanoseconds oscillates. Run it while
        the inputs of the circuit don't change. The ones that change the most come first.

        Args:
            ns: How long it runs, in nanoseconds.
            changes: How many changes make an oscillation.
        """
        ports = [
            port
            for component in self.get_toplevel_components()
            for port in component.ports
            if port.is_output()
        ]
        counts = dict.fromkeys(ports, 0)
        values = [port.value for port in ports]
        for _ in range(ns):
            self.run(ns=1)
            for number, port in enumerate(ports):
                value = port.value
                if value != values[number]:
                    counts[port] += 1
                    values[number] = value
        found = [port for port in ports if counts[port] >= changes]
        return sorted(found, key=lambda port: -counts[port])

    def run_until(
        self,
        s: float | None = None,
        ms: float | None = None,
        us: float | None = None,
        ns: float | None = None,
    ) -> None:
        """
        Run the simulation until an absolute time, nothing happens if it has passed.
        The times are added together.

        Args:
            s: Seconds.
            ms: Milliseconds.
            us: Microseconds.
            ns: Nanoseconds.
        """
        stop_time_ns = self._time_to_ns(s=s, ms=ms, us=us, ns=ns)
        if stop_time_ns >= self._time_ns:
            self.run(ns=stop_time_ns - self._time_ns)

    def add_event(self, port: EventPort, value: VALUE_TYPE, propagation_delay_ns: int) -> None:
        """Add an event for a port, used by the components"""
        event_time_ns = self._time_ns + propagation_delay_ns
        # Set without an __init__, to save a Python call for every event
        event = CircuitEvent(event_time_ns)
        event._time_ns = event_time_ns
        event._port = port
        event._value = value
        self._events_by_port[port] = event
        heapq.heappush(self._circuit_events, event)

    def add_component(self, component: Component) -> None:
        """Add a component to the circuit, components do it when they are created"""
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
        other = self._components.get(name)
        if other is not None and comp.is_toplevel() and not other.is_toplevel():
            # The name of a part of another component (like a gate of an SR) is not saved,
            # the part gets another name: the wires of a loaded file are to the component
            del self._components[name]
            comp.set_name(name, update_circuit=False)
            self._components[name] = comp
            self.add_component(other)
            return
        comp.set_name(name, update_circuit=False)
        self.add_component(comp)

    def get_component(self, component_name: str) -> Component:
        """
        Get a component by its name.

        Raises:
            CircuitError: If the circuit has no component with the name.
        """
        comp = self._components.get(component_name)
        if comp is not None:
            return comp
        raise CircuitError(f"Component '{component_name}' not found")

    def to_dataclass(self, folder: str = ".") -> CircuitDataClass:
        """
        The circuit as a data class, used when saving it.

        Args:
            folder: File paths, like a Verilog file, are stored relative to this folder.
        """
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
        """
        Replace the circuit's components with the ones in a data class.

        Args:
            circuit_dc: The circuit data class, for example from a loaded file.
            folder: The folder that relative file paths are read from.
            component_exceptions: Raise when a component can't be created, otherwise
                skip it and report it in the returned list.
            connect_exceptions: Raise when a wire can't be connected, otherwise skip it
                and report it in the returned list.

        Returns:
            The errors for the skipped components and wires.
        """
        self._folder = folder
        self.clear()

        exception_str_list = []
        for component in circuit_dc.components:
            try:
                with self.adding_components():
                    component.create(self)
            except (DigsimException, FileNotFoundError) as exc:
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

    def to_json_file(self, filename: str | Path) -> None:
        """
        Save the circuit in a JSON file. File paths in it, like a Verilog file, are stored
        relative to the file's folder. The circuit needs a name.
        """
        circuitfile_dc = CircuitFileDataClass(
            circuit=self.to_dataclass(str(Path(filename).parent))
        )
        circuitfile_dc.save(filename)

    def from_json_file(self, filename: str | Path, folder: str | None = None) -> None:
        """
        Load a circuit from a JSON file, replacing the circuit's components.

        Args:
            filename: The file.
            folder: The folder that relative file paths in the file are read from, by
                default the file's folder (where to_json_file() stores them relative to).
        """
        file_dc = CircuitFileDataClass.load(filename)
        if folder is None:
            folder = str(Path(filename).parent)
        self.from_dataclass(file_dc.circuit, folder)
        # A GUI circuit file has the connections in its lines
        for line in file_dc.lines:
            line.connect(self)
