# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""
A stand-in for cocotb's compiled `cocotb.simulator` module, on a DigSim circuit: cocotb's
Python code talks to a simulator only through this module. The `_Scheduler` runs the
circuit and calls cocotb's callbacks in the phases of a time step (timed, value change,
ReadWrite, ReadOnly, NextTimeStep).

The top module has its ports and the named signals inside it (the wires and registers that
synthesis keeps, see YosysComponent's 'signals'), with the submodules of a dotted name like
"alu.out" as modules. Only the inputs of the top module can be set.

Time: one DigSim nanosecond is one picosecond for cocotb (precision 1e-12), so that the
1 ns delay of every gate is short against the clock periods of cocotb tests.
"""

from __future__ import annotations

import heapq
import importlib.metadata
import itertools
import logging
import traceback
from collections.abc import Callable, Iterator
from typing import Any

from digsim.circuit import Circuit
from digsim.circuit.components import YosysComponent
from digsim.circuit.components.atoms import VALUE_TYPE, Component, Port


# The object types (cocotb only compares them with these names)
UNKNOWN = 0
MEMORY = 1
MODULE = 2
NETARRAY = 3
ENUM = 4
STRUCTURE = 5
REAL = 6
INTEGER = 7
STRING = 8
GENARRAY = 9
PACKAGE = 10
PACKED_ARRAY = 11
LOGIC = 12
LOGIC_ARRAY = 13
PACKED_STRUCT = 14
PACKED_UNION = 15
FIXED_STRING = 16
# cocotb 2.1 (later cocotb has PACKED_ARRAY, PACKED_STRUCT and PACKED_UNION)
PACKED = 17

# Iteration modes
OBJECTS = 1
DRIVERS = 2
LOADS = 3

# Edges of value change callbacks
RISING = 1
FALLING = 2
VALUE_CHANGE = 3

# Range directions
RANGE_NO_DIR = 0
RANGE_UP = 1
RANGE_DOWN = -1

# Set actions (the values of cocotb.handle._GPISetAction)
_DEPOSIT = 0
_NO_DELAY = 3

_TYPE_STRINGS = {MODULE: "GPI_MODULE", LOGIC: "GPI_LOGIC", LOGIC_ARRAY: "GPI_LOGIC_ARRAY"}

_PRECISION = -12

# The logger of cocotb's GPI, for what the GPI would log
_gpi_log = logging.getLogger("gpi")
# The time of a DigSim nanosecond in VCD files
TIMESCALE = "1 ps"


class sim_callback:
    """A registered callback, called once"""

    def __init__(self, func: Callable[..., Any], args: tuple[Any, ...]) -> None:
        self._func = func
        self._args = args
        self._active = True

    def deregister(self) -> None:
        """Don't call the callback"""
        self._active = False


class sim_obj:
    """A simulation object: the top module or one of its ports"""

    def __init__(
        self,
        name: str,
        fullname: str,
        obj_type: int,
        port: Port | None = None,
        definition: str = "",
        definition_file: str = "",
    ) -> None:
        self._name = name
        self._fullname = fullname
        self._type = obj_type
        self._port = port
        self._definition = definition
        self._definition_file = definition_file
        self._children: dict[str, sim_obj] = {}

    def _signal(self) -> Port:
        if self._port is None:
            raise TypeError(f"{self._fullname} is not a signal")
        return self._port

    def get_const(self) -> bool:
        return False

    def get_definition_file(self) -> str:
        return self._definition_file

    def get_definition_name(self) -> str:
        return self._definition

    def get_handle_by_index(self, index: int) -> sim_obj | None:
        return None

    def get_handle_by_name(self, name: str, discovery_method: Any = None) -> sim_obj | None:
        return self._children.get(name)

    def get_indexable(self) -> bool:
        return False

    def get_name_string(self) -> str:
        return self._name

    def get_fullname_string(self) -> str:
        return self._fullname

    def get_num_elems(self) -> int:
        return self._signal().width if self._port is not None else len(self._children)

    def get_range(self) -> tuple[int, int, int]:
        if self._port is None:
            return 0, 0, RANGE_NO_DIR
        return self._port.width - 1, 0, RANGE_DOWN

    def get_actual(self) -> sim_obj | None:
        return None

    def get_signal_val_binstr(self) -> str:
        port = self._signal()
        value = port.value
        if isinstance(value, int):
            return f"{value:0{port.width}b}"
        return value * port.width

    def get_signal_val_long(self) -> int:
        # An undefined value reads as 0, like a VPI integer value
        value = self._signal().value
        return value if isinstance(value, int) else 0

    def get_signal_val_real(self) -> float:
        raise TypeError(f"{self._fullname} is not a real")

    def get_signal_val_str(self) -> bytes:
        raise TypeError(f"{self._fullname} is not a string")

    def get_signed(self) -> bool:
        return False

    def get_type(self) -> int:
        return self._type

    def get_type_string(self) -> str:
        return _TYPE_STRINGS.get(self._type, "GPI_UNKNOWN")

    def iterate(self, mode: int) -> Iterator[sim_obj]:
        return iter(list(self._children.values()) if mode == OBJECTS else [])

    def _set(self, action: int, value: VALUE_TYPE) -> None:
        # Like the GPI with a write that the simulator rejects: log it and go on (cocotb
        # applies most writes in a callback of its own, where an exception would end the
        # simulation)
        port = self._signal()
        if action not in (_DEPOSIT, _NO_DELAY):
            _gpi_log.error(
                "DigSim can only deposit values, not force or release %s", self._fullname
            )
        elif not port.is_input() or not port.parent().is_toplevel():
            _gpi_log.error(
                "DigSim can only set the inputs of the top module, not %s", self._fullname
            )
        else:
            port.value = value

    def set_signal_val_binstr(self, action: int, value: str) -> None:
        if set(value) <= {"0", "1"}:
            self._set(action, int(value, 2))
        elif set(value) == {"Z"}:
            self._set(action, "Z")
        else:
            # A port is undefined as a whole
            self._set(action, "X")

    def set_signal_val_int(self, action: int, value: int) -> None:
        self._set(action, value & ((1 << self._signal().width) - 1))

    def set_signal_val_real(self, action: int, value: float) -> None:
        raise TypeError(f"{self._fullname} is not a real")

    def set_signal_val_str(self, action: int, value: bytes) -> None:
        raise TypeError(f"{self._fullname} is not a string")


# An iterator over simulation objects
sim_obj_iterator = Iterator


class _Watch:
    """The value change callbacks of a port, and its value when it was last checked"""

    def __init__(self, value: VALUE_TYPE) -> None:
        self.value = value
        self.callbacks: list[tuple[sim_callback, int]] = []


def _logic_type(port: Port) -> int:
    return LOGIC if port.width == 1 else LOGIC_ARRAY


class _Scheduler:
    """Runs a circuit and calls cocotb's callbacks. It initializes the circuit"""

    def __init__(self, circuit: Circuit, top: Component, path: str, args: list[str]) -> None:
        self.circuit = circuit
        self.args = args
        name = top.name()
        circuit.init()
        self.root = sim_obj(name, name, MODULE, definition=name, definition_file=path)
        for port in top.ports:
            child = sim_obj(port.name(), f"{name}.{port.name()}", _logic_type(port), port)
            self.root._children[port.name()] = child
        if isinstance(top, YosysComponent) and top.parameter_get("signals"):
            for signal in top.signal_names():
                self._add_signal(signal, top._signal_port(signal))
        self.running = False
        self._stop = False
        self._stopped_by_cocotb = False
        self._sequence = itertools.count()
        self._timed: list[tuple[int, int, sim_callback]] = []
        self._readwrite: list[sim_callback] = []
        self._readonly: list[sim_callback] = []
        self._nextstep: list[sim_callback] = []
        self._end_of_sim: list[sim_callback] = []
        self._watches: dict[Port, _Watch] = {}

    def _add_signal(self, name: str, port: Port) -> None:
        """A named signal, in modules for the submodules of its name ("alu.out")"""
        parent = self.root
        *modules, leaf = name.split(".")
        for module in modules:
            child = parent._children.get(module)
            if child is None:
                child = sim_obj(module, f"{parent._fullname}.{module}", MODULE)
                parent._children[module] = child
            elif child._type != MODULE:
                # The name of a module is taken by a port or signal
                return
            parent = child
        if leaf not in parent._children:
            parent._children[leaf] = sim_obj(
                leaf, f"{parent._fullname}.{leaf}", _logic_type(port), port
            )

    # Registering

    def timed(self, steps: int, callback: sim_callback) -> sim_callback:
        time_ns = self.circuit.time_ns + steps
        heapq.heappush(self._timed, (time_ns, next(self._sequence), callback))
        return callback

    def value_change(self, obj: sim_obj, callback: sim_callback, edge: int) -> sim_callback:
        port = obj._signal()
        watch = self._watches.get(port)
        if watch is None:
            watch = self._watches[port] = _Watch(port.value)
        watch.callbacks.append((callback, edge))
        return callback

    def add(self, phase: list[sim_callback], callback: sim_callback) -> sim_callback:
        phase.append(callback)
        return callback

    def stop(self) -> None:
        self._stop = True
        self._stopped_by_cocotb = True

    # Running

    def _call(self, callback: sim_callback) -> None:
        if not callback._active or self._stop:
            return
        callback._active = False
        try:
            callback._func(*callback._args)
        except BaseException:  # noqa: BLE001 (like the GPI: end the simulation)
            traceback.print_exc()
            self._stop = True

    def _call_all(self, phase: list[sim_callback]) -> None:
        callbacks = phase[:]
        phase.clear()
        for callback in callbacks:
            self._call(callback)

    def _check_watches(self) -> None:
        """Call the value change callbacks of the ports that changed"""
        for port, watch in list(self._watches.items()):
            value = port.value
            if value == watch.value:
                continue
            watch.value = value
            due = [
                callback
                for callback, edge in watch.callbacks
                if edge == VALUE_CHANGE
                or (edge == RISING and value == 1)
                or (edge == FALLING and value == 0)
            ]
            watch.callbacks = [
                (callback, edge)
                for callback, edge in watch.callbacks
                if callback._active and callback not in due
            ]
            for callback in due:
                self._call(callback)

    def _settle(self) -> None:
        """Process the events of this time step, with value change and ReadWrite callbacks"""
        circuit = self.circuit
        while not self._stop:
            now = circuit.time_ns
            while circuit.process_single_event(stop_time_ns=now)[0]:
                self._check_watches()
                if self._stop:
                    return
            # Writes by the callbacks
            self._check_watches()
            if not self._readwrite:
                return
            self._call_all(self._readwrite)

    def _advance(self) -> bool:
        """Go to the next time step: its first event or timed callback. False at the end"""
        timed = self._timed
        while timed and not timed[0][2]._active:
            heapq.heappop(timed)
        target = timed[0][0] if timed else None
        if not self.circuit.process_single_event(stop_time_ns=target)[0]:
            if target is None:
                return False
            self.circuit.run_until(ns=target)
        self._call_all(self._nextstep)
        self._check_watches()
        now = self.circuit.time_ns
        while timed and timed[0][0] <= now and not self._stop:
            self._call(heapq.heappop(timed)[2])
        return True

    def run(self) -> None:
        """Run until cocotb stops the simulation, or nothing is left to simulate"""
        self.running = True
        try:
            while not self._stop:
                self._settle()
                if self._stop:
                    break
                self._call_all(self._readonly)
                if self._stop or not self._advance():
                    break
        finally:
            self.running = False
        if not self._stopped_by_cocotb:
            self._stop = False
            self._call_all(self._end_of_sim)


_scheduler: _Scheduler | None = None


def install(scheduler: _Scheduler) -> None:
    """Simulate with this scheduler"""
    global _scheduler
    _scheduler = scheduler


def _current() -> _Scheduler:
    if _scheduler is None:
        raise RuntimeError("No simulator available!")
    return _scheduler


# The functions of cocotb.simulator


def get_precision() -> int:
    return _PRECISION


def get_root_handle(name: str | None) -> sim_obj | None:
    root = _current().root
    if name is None or name.casefold() == root.get_name_string().casefold():
        return root
    return None


def root_iterate() -> Iterator[sim_obj]:
    return iter([_current().root])


def package_iterate() -> Iterator[sim_obj]:
    return iter([])


def get_sim_time() -> tuple[int, int]:
    time_ns = _current().circuit.time_ns
    return time_ns >> 32, time_ns & 0xFFFF_FFFF


def get_simulator_product() -> str:
    return "DigSim"


def get_simulator_version() -> str:
    return importlib.metadata.version("digsim-engine")


def get_simulator_args() -> list[str]:
    return list(_current().args)


def is_running() -> bool:
    return _scheduler is not None and _scheduler.running


def set_gpi_log_level(level: int) -> None:
    pass


def initialize_logger(log_func: Callable[..., Any], get_logger: Callable[[str], Any]) -> None:
    pass


def register_nextstep_callback(func: Callable[..., Any], *args: Any) -> sim_callback:
    scheduler = _current()
    return scheduler.add(scheduler._nextstep, sim_callback(func, args))


def register_readonly_callback(func: Callable[..., Any], *args: Any) -> sim_callback:
    scheduler = _current()
    return scheduler.add(scheduler._readonly, sim_callback(func, args))


def register_rwsynch_callback(func: Callable[..., Any], *args: Any) -> sim_callback:
    scheduler = _current()
    return scheduler.add(scheduler._readwrite, sim_callback(func, args))


def register_timed_callback(time: int, func: Callable[..., Any], *args: Any) -> sim_callback:
    return _current().timed(time, sim_callback(func, args))


def register_value_change_callback(
    signal: sim_obj, func: Callable[..., Any], edge: int, *args: Any
) -> sim_callback:
    return _current().value_change(signal, sim_callback(func, args), edge)


def register_end_of_sim_time_callback(func: Callable[..., Any], *args: Any) -> sim_callback:
    scheduler = _current()
    return scheduler.add(scheduler._end_of_sim, sim_callback(func, args))


def set_sim_event_callback(sim_event_callback: Callable[[], object]) -> None:
    """cocotb 2.1, later cocotb registers with register_end_of_sim_time_callback()"""
    register_end_of_sim_time_callback(sim_event_callback)


def stop_simulator() -> None:
    _current().stop()


class cpp_clock:
    """A clock driven by timed callbacks (cocotb's Clock(impl="gpi"))"""

    def __init__(self, obj: sim_obj) -> None:
        self._obj = obj
        self._callback: sim_callback | None = None

    def start(self, period_steps: int, high_steps: int, start_high: bool, set_action: int) -> None:
        self.stop()
        low_steps = period_steps - high_steps

        def toggle(level: int) -> None:
            self._obj.set_signal_val_int(set_action, level)
            self._callback = register_timed_callback(
                high_steps if level else low_steps, toggle, 1 - level
            )

        toggle(1 if start_high else 0)

    def stop(self) -> None:
        if self._callback is not None:
            self._callback.deregister()
            self._callback = None


def clock_create(obj: sim_obj) -> cpp_clock:
    return cpp_clock(obj)


__all__ = [
    "DRIVERS",
    "ENUM",
    "FALLING",
    "FIXED_STRING",
    "GENARRAY",
    "INTEGER",
    "LOADS",
    "LOGIC",
    "LOGIC_ARRAY",
    "MEMORY",
    "MODULE",
    "NETARRAY",
    "OBJECTS",
    "PACKAGE",
    "PACKED",
    "PACKED_ARRAY",
    "PACKED_STRUCT",
    "PACKED_UNION",
    "RANGE_DOWN",
    "RANGE_NO_DIR",
    "RANGE_UP",
    "REAL",
    "RISING",
    "STRING",
    "STRUCTURE",
    "UNKNOWN",
    "VALUE_CHANGE",
    "clock_create",
    "cpp_clock",
    "get_precision",
    "get_root_handle",
    "get_sim_time",
    "get_simulator_args",
    "get_simulator_product",
    "get_simulator_version",
    "initialize_logger",
    "is_running",
    "package_iterate",
    "register_end_of_sim_time_callback",
    "register_nextstep_callback",
    "register_readonly_callback",
    "register_rwsynch_callback",
    "register_timed_callback",
    "register_value_change_callback",
    "root_iterate",
    "set_gpi_log_level",
    "set_sim_event_callback",
    "sim_callback",
    "sim_obj",
    "sim_obj_iterator",
    "stop_simulator",
]
