# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""
The optional native simulation engine (a trial): the digsim_native package, in Rust,
from https://github.com/freand76/digsim-native. Without it, or with
DIGSIM_ENGINE=python, the circuit simulates in Python as before.

DIGSIM_ENGINE selects the engine:
- "native" (the default): the native engine runs the event loop, and simulates the
  Yosys gate cells and the bus ports it knows, the other components are called back in
  Python
- "python": no native code

The ports that the native engine simulates get a subclass of their class while it runs:
their value is read from the engine, and setting them sets them in the engine.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from .components import _yosys_atoms as atoms
from .components import _yosys_functional as functional
from .components._static_level import GND, VDD
from .components._yosys_component import SignalPort, StatePort
from .components.atoms import (
    Component,
    Port,
    PortIn,
    PortMultiBitWire,
    PortOutDelta,
    PortWire,
    PortWireBit,
)
from .components.atoms._port import connection_generation


if TYPE_CHECKING:
    from ._circuit import Circuit

try:
    import digsim_native  # type: ignore[import-untyped, import-not-found, unused-ignore]
except ImportError:
    digsim_native = None


def mode() -> str:
    """The engine to use: "native" or "python" """
    if digsim_native is None:
        return "python"
    return "python" if os.environ.get("DIGSIM_ENGINE") == "python" else "native"


# The native cells, by the class they are made from: the kind (the order of Kind in
# src/lib.rs of digsim-native) and the input ports in the order of the kind
_GATES: dict[type[Component], tuple[int, str]] = {
    atoms._BUF_: (0, "A"),
    atoms._NOT_: (1, "A"),
    atoms._AND_: (2, "AB"),
    atoms._NAND_: (3, "AB"),
    atoms._OR_: (4, "AB"),
    atoms._NOR_: (5, "AB"),
    atoms._XOR_: (6, "AB"),
    atoms._XNOR_: (7, "AB"),
    atoms._ANDNOT_: (8, "AB"),
    atoms._ORNOT_: (9, "AB"),
    atoms._MUX_: (10, "ABS"),
    atoms._NMUX_: (11, "ABS"),
    atoms._MUX4_: (12, "ABCDST"),
    atoms._MUX8_: (13, "ABCDEFGHSTU"),
    atoms._MUX16_: (14, "ABCDEFGHIJKLMNOPSTUV"),
    atoms._AOI3_: (15, "ABC"),
    atoms._OAI3_: (16, "ABC"),
    atoms._AOI4_: (17, "ABCD"),
    atoms._OAI4_: (18, "ABCD"),
    atoms._TBUF_: (26, "AE"),
}
# Flip-flops, latches and GND/VDD, by their base class
_STATEFUL: dict[type[Component], int] = {
    atoms._DFF_: 19,
    atoms._DFFE2_: 20,
    atoms._DFF3_: 21,
    atoms._DFFE4_: 22,
    atoms._SDFF_: 23,
    atoms._SDFFE_: 24,
    atoms._SDFFCE_: 25,
    GND: 27,
    VDD: 27,
    atoms._SR_: 28,
    atoms._DLATCH_: 29,
    atoms._DLATCH3_: 30,
    atoms._DLATCHSR_: 31,
    atoms._ALDFF_: 32,
    atoms._ALDFFE_: 33,
    atoms._DFFSR_: 34,
    atoms._DFFSRE_: 35,
}
# The inputs of the stateful cells (those it has), and their levels
_STATEFUL_INPUTS = ("C", "D", "E", "R", "S", "L", "AD")
_LEVELS = (
    "_clock_edge",
    "_reset_level",
    "_reset_value",
    "_enable_level",
    "_set_level",
    "_load_level",
)
# The native functional cells, by their class: the kind (the order of KINDS in
# src/word.rs of digsim-native). Their inputs are in the order they are added.
_FUNCTIONAL_CLASSES: list[list[type[functional.FunctionalCell]]] = [
    [functional.Not],
    [functional.Pos, functional.Buf],
    [functional.Neg],
    [functional.And],
    [functional.Or],
    [functional.Xor],
    [functional.Xnor],
    [functional.ReduceAnd],
    [functional.ReduceOr, functional.ReduceBool],
    [functional.ReduceXor],
    [functional.ReduceXnor],
    [functional.LogicNot],
    [functional.LogicAnd],
    [functional.LogicOr],
    [functional.Shl, functional.Sshl],
    [functional.Shr],
    [functional.Sshr],
    [functional.Shift],
    [functional.Shiftx],
    [functional.Lt],
    [functional.Le],
    [functional.Gt],
    [functional.Ge],
    [functional.Eq],
    [functional.Ne],
    [functional.Eqx],
    [functional.Nex],
    [functional.Add],
    [functional.Sub],
    [functional.Mul],
    [functional.Div],
    [functional.Mod],
    [functional.DivFloor],
    [functional.ModFloor],
    [functional.Pow],
    [functional.Mux],
    [functional.Pmux],
    [functional.Bmux],
    [functional.Demux],
    [functional.Bwmux],
    [functional.Dff],
    [functional.Dffe],
    [functional.Adff],
    [functional.Adffe],
    [functional.Aldff],
    [functional.Aldffe],
    [functional.Sdff],
    [functional.Sdffe],
    [functional.Sdffce],
    [functional.Dffsr],
    [functional.Dffsre],
    [functional.Dlatch],
    [functional.Adlatch],
    [functional.Dlatchsr],
    [functional.Sr],
    [functional.Decoder],
    [functional.Alu],
    [functional.Lcu],
    [functional.Fa],
    [functional.MaccV2],
    [functional.Lut],
    [functional.Sop],
    [functional.Bweqx],
    [functional.Concat],
    [functional.Slice],
    [functional.Tribuf],
]
_FUNCTIONAL: dict[type[functional.FunctionalCell], int] = {
    cls: kind for kind, classes in enumerate(_FUNCTIONAL_CLASSES) for cls in classes
}
# Port kinds, as in src/lib.rs of digsim-native
_PY, _IN, _WIRE, _OUT, _BIT, _BUS, _CELL_INPUT, _WORD = range(8)
# Bus ports that work the same natively, they don't change how the value is handled
_BUS_CLASSES = (PortMultiBitWire, SignalPort, StatePort)
_NONE = 2**32 - 1
_CODES: dict[Any, int] = {0: 0, 1: 1, "X": 2, "Z": 3}


def _cell(component: Component) -> tuple[int, list[Port | None], list[int]] | None:
    """The native kind, input ports and levels of a component, None if it isn't one"""
    gate = _GATES.get(type(component))
    if gate is not None:
        kind, names = gate
        return kind, [component.port(name) for name in names], [0] * len(_LEVELS)
    for base in type(component).__mro__:
        stateful = _STATEFUL.get(base)
        if stateful is None:
            continue
        port_names = {port.name() for port in component.ports}
        inputs = [
            component.port(name) if name in port_names else None for name in _STATEFUL_INPUTS
        ]
        levels = [getattr(component, attribute, 0) for attribute in _LEVELS]
        return stateful, inputs, levels
    return None


def _plain(port: Port) -> bool:
    """A port without several drivers or its own set_value()"""
    return port._drivers is None and "set_value" not in port.__dict__


def _resolved(port: Port) -> bool:
    """A port of one bit with several drivers, the engine resolves its value"""
    drivers = port._drivers
    return (
        drivers is not None
        and port.width == 1
        and port.__dict__.get("set_value") == drivers.set_value
        and all(driver.width == 1 for driver in drivers.drivers)
    )


def _driven_natively(port: Port) -> bool:
    """A port that the engine can set: one driver, or one bit and several"""
    return _plain(port) or _resolved(port)


def _can_be_native(component: Component) -> bool:
    """A cell whose ports work the same natively: one bit each"""
    for port in component.ports:
        if port.width != 1 or not _driven_natively(port):
            return False
        if port.is_output():
            if type(port) is not PortOutDelta or port._update_parent:
                return False
        elif type(port) not in (PortIn, PortWire):
            return False
    return True


def _word_cell_can_be_native(component: Component) -> bool:
    """A functional cell whose ports work the same natively"""
    if type(component) not in _FUNCTIONAL:
        return False
    assert isinstance(component, functional.FunctionalCell)
    for port in component.ports:
        if not _driven_natively(port):
            return False
        if port.is_output():
            if type(port) is not PortOutDelta or port._update_parent:
                return False
        elif type(port) is not functional._CellInput:
            return False
    return all(type(port) is functional._WordOut for port in component._word_outputs.values())


def _native_word_cells(components: list[Component]) -> list[functional.FunctionalCell]:
    """
    The functional cells to simulate natively. Cells linked as words are both native or
    both Python, so a cell that can't be native keeps the cells it is linked to in Python.
    """
    cells = [c for c in components if isinstance(c, functional.FunctionalCell)]
    native = {cell for cell in cells if _word_cell_can_be_native(cell)}
    changed = True
    while changed:
        changed = False
        for cell in cells:
            for word_output in cell._word_outputs.values():
                for target in word_output._links:
                    if (cell in native) != (target in native):
                        native.discard(cell)
                        native.discard(target)
                        changed = True
    return [cell for cell in cells if cell in native]


def _bus_can_be_native(port: Port) -> bool:
    """A bus port, of at most 64 bits, that works the same natively"""
    if type(port) not in _BUS_CLASSES or port.width > 64 or not _plain(port):
        return False
    bits = port._bits  # type: ignore[attr-defined]
    return all(type(bit) is PortWireBit and _driven_natively(bit) for bit in bits)


class NativeEngine:
    """The native engine of a circuit, and the Python ports it took over"""

    def __init__(self, circuit: Circuit, time_ns: int) -> None:
        components = list(circuit._components.values())
        cells: dict[Component, tuple[int, list[Port | None], list[int]]] = {}
        for component in components:
            found = _cell(component)
            if found is not None and _can_be_native(component):
                cells[component] = found
        self.cells = list(cells)
        cell_index = {component: index for index, component in enumerate(self.cells)}
        self.word_cells = _native_word_cells(components)
        self._word_index = {cell: number for number, cell in enumerate(self.word_cells)}

        # Every port that can have an event or be driven: the components' ports (also the
        # ones a component keeps for itself, like the feedback of a clock), the bits of
        # bus ports, and the ports they drive
        self.ports: list[Port] = []
        index: dict[int, int] = {}

        def add(port: Port) -> None:
            if id(port) not in index:
                index[id(port)] = len(self.ports)
                self.ports.append(port)

        for component in components:
            for port in [*component.ports, *vars(component).values()]:
                if isinstance(port, Port):
                    add(port)
            if isinstance(component, functional.FunctionalCell):
                for port in component._word_outputs.values():
                    add(port)
        position = 0
        while position < len(self.ports):
            port = self.ports[position]
            for target in port.wired_ports:
                add(target)
            if port._drivers is not None:
                for driver in port._drivers.drivers:
                    add(driver)
            if isinstance(port, PortMultiBitWire):
                for bit in port._bits:
                    add(bit)
            elif isinstance(port, PortWireBit):
                add(port.get_parent_port())
            position += 1

        buses = [port for port in self.ports if _bus_can_be_native(port)]
        bus_index = {id(port): number for number, port in enumerate(buses)}
        kinds = []
        owners = []
        aux = []
        # The input and bit of each input bit of a functional cell, the output of a word port
        word_ports: dict[int, int] = {}
        for word_cell_component in self.word_cells:
            bits = word_cell_component._bits
            for input_number, name in enumerate(word_cell_component._inputs):
                for bit_number, bit_port in enumerate(bits[name]):
                    word_ports[id(bit_port)] = input_number << 20 | bit_number
            for output_number, name in enumerate(word_cell_component._outputs):
                word_output = word_cell_component._word_outputs.get(name)
                if word_output is not None:
                    word_ports[id(word_output)] = output_number
        for port in self.ports:
            cell = cell_index.get(port.parent())
            aux.append(word_ports.get(id(port), 0))
            word_cell = self._word_index.get(port.parent())  # type: ignore[call-overload]
            if word_cell is not None:
                if isinstance(port, functional._CellInput):
                    kinds.append(_CELL_INPUT)
                elif isinstance(port, functional._WordOut):
                    kinds.append(_WORD)
                else:
                    kinds.append(_OUT)
                owners.append(word_cell)
            elif id(port) in bus_index:
                kinds.append(_BUS)
                owners.append(bus_index[id(port)])
            elif isinstance(port, PortWireBit) and id(port.get_parent_port()) in bus_index:
                kinds.append(_BIT)
                owners.append(index[id(port.get_parent_port())])
            elif cell is None or isinstance(port, PortMultiBitWire):
                kinds.append(_PY)
                owners.append(_NONE)
            elif port.is_output():
                kinds.append(_OUT)
                owners.append(cell)
            else:
                kinds.append(_IN if type(port) is PortIn else _WIRE)
                owners.append(cell)
        native_cells = []
        for component, (kind, inputs, levels) in cells.items():
            native_cells.append(
                (
                    kind,
                    [_NONE if port is None else index[id(port)] for port in inputs],
                    index[id(component.outports()[0])],
                    levels,
                    _CODES.get(getattr(component, "_old_C_level", "X"), 2),
                )
            )
        self.engine = digsim_native.Engine(
            self.ports,
            kinds,
            owners,
            [_CODES.get(port._value, 2) if port.width == 1 else 2 for port in self.ports],
            [[index[id(target)] for target in port.wired_ports] for port in self.ports],
            [
                [index[id(driver)] for driver in port._drivers.drivers]  # type: ignore[union-attr]
                if kind != _PY and _resolved(port)
                else []
                for port, kind in zip(self.ports, kinds, strict=True)
            ],
            [getattr(port, "_delay_ns", 0) for port in self.ports],
            [port.parent().is_toplevel() for port in self.ports],
            native_cells,
            [([index[id(bit)] for bit in bus._bits], bus._value) for bus in buses],  # type: ignore[attr-defined]
            aux,
            [self._word_cell(cell, index) for cell in self.word_cells],
            time_ns,
        )
        self.generation = connection_generation.value
        for nid, port in enumerate(self.ports):
            port._nid = nid  # type: ignore[attr-defined]
        # The ports that the engine simulates read and set their values in it
        self._native_ports = [
            port for port, kind in zip(self.ports, kinds, strict=True) if kind != _PY
        ]
        classes: dict[type[Port], type[Port]] = {}
        for port, kind in zip(self.ports, kinds, strict=True):
            if kind == _PY:
                continue
            cls = type(port)
            if cls not in classes:
                classes[cls] = self._native_class(cls, driven=kind != _OUT)
            port.__class__ = classes[cls]
        # A port with several drivers has the set_value() of its _Drivers, which resolves
        # in Python: the engine does it for the ports it sets
        self._resolved_ports = [
            port
            for port, kind in zip(self.ports, kinds, strict=True)
            if kind != _PY and _resolved(port)
        ]
        for port in self._resolved_ports:
            port.set_value = self._resolved_set_value(port)  # type: ignore[method-assign]

    def _word_cell(
        self, cell: functional.FunctionalCell, index: dict[int, int]
    ) -> tuple[Any, ...]:
        """A functional cell for the engine"""
        inputs = [
            (len(cell._bits[name]), name in cell._updating_inputs, word[0], word[1])
            for name, word in cell._inputs.items()
        ]
        outputs = []
        for name, last in cell._outputs.items():
            ports = cell._bits[name]
            mask = (1 << len(ports)) - 1
            word_output = cell._word_outputs.get(name)
            links = []
            if word_output is not None:
                for target, target_links in word_output._links.items():
                    names = list(target._inputs)
                    links.append(
                        (
                            self._word_index[target],
                            [
                                (names.index(port), offset, start, width)
                                for port, offset, start, width in target_links
                            ],
                        )
                    )
            outputs.append(
                (
                    len(ports),
                    [index[id(port)] for port in ports],
                    cell._bit_outputs.get(name, mask),
                    None if word_output is None else index[id(word_output)],
                    links,
                    last,
                )
            )
        parameters = {name: cell.param(name) for name in cell._cell.parameters}
        q = getattr(cell, "_q", (0, 0))
        clock = _CODES.get(getattr(cell, "_old_clock", "X"), 2)
        driving = getattr(cell, "_driving", True)
        return (_FUNCTIONAL[type(cell)], inputs, outputs, parameters, q, clock, driving)

    def default_state(self, component: Component) -> bool:
        """Set the default state of a component the engine simulates, False if it doesn't"""
        number = self._word_index.get(component)  # type: ignore[call-overload]
        if number is None:
            return False
        self.engine.word_default_state(number)
        return True

    def _resolved_set_value(self, port: Port) -> Any:
        """The set_value() of a port that the engine resolves, the value is ignored"""
        engine = self.engine

        def set_value(value: Any) -> None:
            engine.set_input(port._nid, value)  # type: ignore[attr-defined]

        return set_value

    def _native_class(self, cls: type[Port], driven: bool) -> type[Port]:
        """A subclass of a port class for ports that the engine simulates"""
        engine = self.engine

        def get_value(port: Port) -> Any:
            return engine.value(port._nid)  # type: ignore[attr-defined]

        def set_raw(port: Port, value: Any) -> None:
            engine.set_raw(port._nid, value)  # type: ignore[attr-defined]

        namespace: dict[str, Any] = {"_value": property(get_value, set_raw)}
        if driven:
            base_set_value = cls.set_value

            def set_value(port: Port, value: Any) -> None:
                if type(port) is native_class:
                    engine.set_input(port._nid, value)  # type: ignore[attr-defined]
                else:
                    # The port is back in Python, but a port with several drivers keeps
                    # the set_value() it had when it got its second driver (see _Drivers)
                    base_set_value(port, value)

            namespace["set_value"] = set_value
        native_class = type(cls.__name__, (cls,), namespace)
        return native_class

    def nid(self, port: Port) -> int:
        """The index of a port in the engine, a Python port it doesn't have is added"""
        nid = getattr(port, "_nid", None)
        if nid is None:
            # Its targets first, the ports it drives
            wired = [self.nid(target) for target in port.wired_ports]
            nid = self.engine.add_port(port, wired, port.parent().is_toplevel())
            port._nid = nid  # type: ignore[attr-defined]
            self.ports.append(port)
        return int(nid)

    def close(self) -> tuple[list[tuple[int, int, Port, Any]], dict[int, int], int]:
        """
        Give the ports back to Python. Returns the events in the order of the heap as
        (time, seq, port, value), the seq of the latest event of each port (by id()),
        and the time.
        """
        events, latest, clocks = self.engine.export()
        for port in self._resolved_ports:
            # Unless a removed driver left it with one, it resolves in Python again
            if port._drivers is not None:
                port.set_value = port._drivers.set_value  # type: ignore[method-assign]
        for port in self._native_ports:
            value = port._value
            port.__class__ = type(port).__mro__[1]
            port._value = value
        for port in self.ports:
            del port._nid  # type: ignore[attr-defined]
        for component, clock in zip(self.cells, clocks, strict=True):
            if hasattr(component, "_old_C_level"):
                setattr(component, "_old_C_level", clock)  # noqa: B010
        for cell, (inputs, outputs, q, clock, driving) in zip(
            self.word_cells, self.engine.export_words(), strict=True
        ):
            # In place: the input bits keep the list of their word
            for word, (bits, undefined) in zip(cell._inputs.values(), inputs, strict=True):
                word[0], word[1] = bits, undefined
            for name, last in zip(list(cell._outputs), outputs, strict=True):
                cell._outputs[name] = last
            if isinstance(cell, functional._Register):
                cell._q = q
                cell._old_clock = clock
            if isinstance(cell, functional.Tribuf):
                cell._driving = driving
        ports = self.ports
        return (
            [(time, seq, ports[nid], value) for time, seq, nid, value in events],
            {id(ports[nid]): seq for nid, seq in enumerate(latest) if seq is not None},
            self.engine.time,
        )
