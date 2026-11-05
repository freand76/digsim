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

import functools
import os
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, NamedTuple

from .components import _yosys_atoms as atoms
from .components import _yosys_functional as functional
from .components._static_level import GND, VDD
from .components._yosys_component import SignalPort, StatePort, YosysComponent
from .components.atoms import (
    VALUE_TYPE,
    Component,
    DigsimException,
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
_PY, _IN, _WIRE, _OUT, _BIT, _BUS, _CELL_INPUT, _WORD, _BLOCK_PIN, _BLOCK_INNER = range(10)
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


class _BlockCell(NamedTuple):
    """A cell of a block: its component, and its arguments for the engine but the word cell"""

    component: Component
    op: int  # 0 functional, 1 gate, 2 constant
    kind: int
    inputs: list[tuple[list[tuple[int, int]], bool]]
    outputs: list[int]
    stateful: bool
    levels: list[int]
    clock: int
    value: int


class _BlockPlan(NamedTuple):
    """A Yosys component compiled to one block of the engine (see src/block.rs)"""

    component: YosysComponent
    members: set[Component]
    widths: list[int]
    cells: list[_BlockCell]
    ranks: list[int]
    # The (slot, bit) of each port of the members, by id()
    bits: dict[int, tuple[int, int]]


def _block_plan(component: YosysComponent) -> _BlockPlan | None:
    """
    The block of a Yosys component, None if it can't be one: the native engine simulates
    it as one block, the combinational cells in the order of their ranks without events
    in between (like a compiled simulator), instead of with a delay for each cell. A
    netlist with a combinational loop, tristate buffers or inout ports, or cells it
    doesn't have, keeps the cells.
    """
    if os.environ.get("DIGSIM_BLOCKS") == "0":
        return None
    try:
        parts = component.netlist_parts()
    except DigsimException:
        return None
    if any(port.is_inout for port in parts.ports.values()):
        return None
    members = set(parts.components.values())
    widths = [1, 1]  # GND and VDD
    net_bits: dict[Any, tuple[int, int]] = {"0": (0, 0), "1": (1, 0)}
    for module_port in parts.ports.values():
        if module_port.is_output:
            continue
        slot = len(widths)
        widths.append(len(module_port.bits))
        for bit, net in enumerate(module_port.bits):
            net_bits.setdefault(net, (slot, bit))
    # The cells and their output slots, then their inputs (they need all outputs)
    found: list[tuple[Component, Any, list[int]]] = []
    for cellname, yosys_cell in parts.cells.items():
        cell_component = parts.components.get(cellname)
        if cell_component is None:
            continue
        outputs: list[int] = []
        if isinstance(cell_component, functional.FunctionalCell):
            if (
                not _word_cell_can_be_native(cell_component)
                or isinstance(cell_component, functional.Tribuf)
                or cell_component._word_outputs.keys() - cell_component._outputs.keys()
            ):
                return None
            for name in cell_component._outputs:
                slot = len(widths)
                widths.append(len(cell_component._bits[name]))
                outputs.append(slot)
                for bit, net in enumerate(yosys_cell.connections[name]):
                    net_bits[net] = (slot, bit)
        else:
            gate = _cell(cell_component)
            if gate is None or gate[0] in (26, 27) or not _can_be_native(cell_component):
                return None
            output = cell_component.outports()[0]
            slot = len(widths)
            widths.append(1)
            outputs.append(slot)
            net_bits[yosys_cell.connections[output.name()][0]] = (slot, 0)
        found.append((cell_component, yosys_cell, outputs))

    def net_bit(net: Any) -> tuple[int, int]:
        return net_bits.get(net, (_NONE, 0))

    bits: dict[int, tuple[int, int]] = {}
    cells: list[_BlockCell] = []
    for cell_component, yosys_cell, outputs in found:
        inputs: list[tuple[list[tuple[int, int]], bool]] = []
        if isinstance(cell_component, functional.FunctionalCell):
            stateful = isinstance(cell_component, functional._Register)
            for name in cell_component._inputs:
                nets = yosys_cell.connections[name]
                update = name in cell_component._updating_inputs
                if not stateful and not update:
                    return None
                inputs.append(([net_bit(net) for net in nets], update))
                for bit_port, net in zip(cell_component._bits[name], nets, strict=True):
                    bits[id(bit_port)] = net_bit(net)
            for name, slot in zip(cell_component._outputs, outputs, strict=True):
                for bit, bit_port in enumerate(cell_component._bits[name]):
                    bits[id(bit_port)] = (slot, bit)
            cells.append(
                _BlockCell(cell_component, 0, 0, inputs, outputs, stateful, [0] * 6, 2, 0)
            )
            continue
        kind, ports, levels = _cell(cell_component)  # type: ignore[misc]
        stateful = kind >= 19
        names = _GATES[type(cell_component)][1] if not stateful else _STATEFUL_INPUTS
        names_list = list(names) if not stateful else list(_STATEFUL_INPUTS)
        for name, gate_port in zip(names_list, ports, strict=True):
            if gate_port is None:
                inputs.append(([(_NONE, 0)], False))
                continue
            update = type(gate_port) is PortIn
            if not stateful and not update:
                return None
            net = yosys_cell.connections[name][0]
            inputs.append(([net_bit(net)], update))
            bits[id(gate_port)] = net_bit(net)
        bits[id(cell_component.outports()[0])] = (outputs[0], 0)
        clock = _CODES.get(getattr(cell_component, "_old_C_level", "X"), 2)
        cells.append(
            _BlockCell(cell_component, 1, kind, inputs, outputs, stateful, levels, clock, 0)
        )
    for value, name in ((0, "GND"), (1, "VDD")):
        constant = parts.components[name]
        bits[id(constant.port("O"))] = (value, 0)
        cells.append(_BlockCell(constant, 2, 27, [], [value], True, [0] * 6, 2, value))
    # The ranks of the combinational cells: above the cells that drive them
    producer = {slot: number for number, c in enumerate(cells) for slot in c.outputs}
    drivers: list[set[int]] = []
    for block_cell in cells:
        sources = set()
        if not block_cell.stateful:
            for input_bits, _update in block_cell.inputs:
                for slot, _bit in input_bits:
                    producer_cell = producer.get(slot)
                    if producer_cell is not None and not cells[producer_cell].stateful:
                        sources.add(producer_cell)
        drivers.append(sources)
    driven: list[list[int]] = [[] for _ in cells]
    for number, sources in enumerate(drivers):
        for source in sources:
            driven[source].append(number)
    ranks = [-1] * len(cells)
    waiting = [len(sources) for sources in drivers]
    ready = [n for n, c in enumerate(cells) if not c.stateful and not waiting[n]]
    for number in ready:
        ranks[number] = 0
    while ready:
        number = ready.pop()
        for target in driven[number]:
            ranks[target] = max(ranks[target], ranks[number] + 1)
            waiting[target] -= 1
            if not waiting[target]:
                ready.append(target)
    if any(rank < 0 for rank, c in zip(ranks, cells, strict=True) if not c.stateful):
        return None  # A combinational loop
    ranks = [_NONE if c.stateful else rank for rank, c in zip(ranks, cells, strict=True)]
    for member in members:
        for member_port in member.ports:
            if not member_port.is_input():
                continue
            if member_port.wired_ports or member_port._drivers is not None:
                return None
            member_driver = member_port.get_driver()
            # Driven from outside: the bit must be one of an input of the module
            outside = member_driver is not None and member_driver.parent() not in members
            if outside and bits.get(id(member_port), (_NONE, 0))[0] == _NONE:
                return None
    return _BlockPlan(component, members, widths, cells, ranks, bits)


class NativeEngine:
    """The native engine of a circuit, and the Python ports it took over"""

    def __init__(self, circuit: Circuit, time_ns: int) -> None:
        components = list(circuit._components.values())
        # The Yosys components compiled to blocks, and the block of each of their cells
        self.blocks: list[_BlockPlan] = []
        self._member_block: dict[Component, int] = {}
        for component in components:
            if isinstance(component, YosysComponent):
                plan = _block_plan(component)
                if plan is not None:
                    for member in plan.members:
                        self._member_block[member] = len(self.blocks)
                    self.blocks.append(plan)
        self._blocks_defaulted: set[int] = set()
        members = self._member_block
        cells: dict[Component, tuple[int, list[Port | None], list[int]]] = {}
        for component in components:
            if component in members:
                continue
            found = _cell(component)
            if found is not None and _can_be_native(component):
                cells[component] = found
        self.cells = list(cells)
        cell_index = {component: index for index, component in enumerate(self.cells)}
        self.word_cells = _native_word_cells([c for c in components if c not in members])
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
        # The ports of the blocks: (slot, bit) of each, and the pins
        block_bits: list[tuple[int, int]] = []
        block_pins: list[list[tuple[int, int, int]]] = [[] for _ in self.blocks]
        block_vcd: list[list[tuple[int, int, int]]] = [[] for _ in self.blocks]
        # The ports of the blocks that drive ports outside, and those they drive
        self._outside: dict[int, list[Port]] = {}
        for nid, port in enumerate(self.ports):
            number = members.get(port.parent())
            if number is None:
                continue
            plan = self.blocks[number]
            slot, bit_index = plan.bits.get(id(port), (_NONE, 0))
            if port.is_output():
                outside = [t for t in port.wired_ports if t.parent() not in plan.members]
                if outside and slot != _NONE:
                    self._outside[nid] = outside
                    block_pins[number].append((slot, bit_index, nid))
                if slot != _NONE and not isinstance(port, functional._WordOut):
                    block_vcd[number].append((slot, bit_index, nid))
        outside_ids = {id(self.ports[nid]) for nid in self._outside}
        # One input of a block for each bit it gets from outside: the ports of the other
        # cells on the bit read it from the block
        self._pins: set[int] = set()
        seen: set[tuple[int, int, int]] = set()
        for port in self.ports:
            number = members.get(port.parent())
            if number is None or port.is_output():
                continue
            plan = self.blocks[number]
            source = port.get_driver()
            if source is None or source.parent() in plan.members:
                continue
            key = (number, *plan.bits[id(port)])
            if key not in seen:
                seen.add(key)
                self._pins.add(id(port))
        for port in self.ports:
            number = members.get(port.parent())
            if number is not None:
                plan = self.blocks[number]
                owners.append(number)
                aux.append(len(block_bits))
                block_bits.append(plan.bits.get(id(port), (_NONE, 0)))
                if id(port) in self._pins:
                    kinds.append(_BLOCK_PIN)
                elif id(port) in outside_ids:
                    kinds.append(_OUT)
                else:
                    kinds.append(_BLOCK_INNER)
                continue
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
            [
                [index[id(target)] for target in self._wired(nid, port)]
                for nid, port in enumerate(self.ports)
            ],
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
            [
                self._block_args(plan, block_pins[number], block_vcd[number])
                for number, plan in enumerate(self.blocks)
            ],
            block_bits,
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
        # The Python ports that the engine sets itself, without calling their set_value()
        fast: list[tuple[int, int, Callable[[], None] | None]] = []
        for nid, (port, kind) in enumerate(zip(self.ports, kinds, strict=True)):
            if kind != _PY or port._drivers is not None:
                continue
            if (
                type(port) is PortOutDelta
                and not port._update_parent
                and "delta_cycle" not in port.__dict__
            ):
                # Its events set the ports it drives in the engine
                fast.append((nid, 3, None))
                continue
            if port.wired_ports or "set_value" in port.__dict__:
                continue
            if type(port) is PortIn:
                fast.append((nid, 1, port.parent().update))
            elif type(port) is PortWire:
                fast.append((nid, 2, None))
        self.engine.set_fast_ports(fast)

    def _wired(self, nid: int, port: Port) -> list[Port]:
        """The ports a port drives in the engine: a block drives its cells itself"""
        members = self._member_block
        if port.parent() in members:
            return self._outside.get(nid, [])
        return [t for t in port.wired_ports if t.parent() not in members or id(t) in self._pins]

    def _block_args(
        self,
        plan: _BlockPlan,
        pins: list[tuple[int, int, int]],
        vcd: list[tuple[int, int, int]],
    ) -> tuple[Any, ...]:
        """A block for the engine"""
        cells = []
        for cell, rank in zip(plan.cells, plan.ranks, strict=True):
            word = None
            if cell.op == 0:
                component = cell.component
                assert isinstance(component, functional.FunctionalCell)
                inputs = [
                    (len(component._bits[name]), name in component._updating_inputs, w[0], w[1])
                    for name, w in component._inputs.items()
                ]
                outputs: list[tuple[Any, ...]] = [
                    (len(component._bits[name]), [], 0, None, [], last)
                    for name, last in component._outputs.items()
                ]
                parameters = {name: component.param(name) for name in component._cell.parameters}
                q = getattr(component, "_q", (0, 0))
                clock = _CODES.get(getattr(component, "_old_clock", "X"), 2)
                kind = _FUNCTIONAL[type(component)]
                word = (kind, inputs, outputs, parameters, q, clock, True)
                old_clock = clock
            else:
                old_clock = cell.clock
            cells.append(
                (
                    cell.op,
                    cell.kind,
                    cell.inputs,
                    cell.outputs,
                    rank,
                    word,
                    cell.levels,
                    old_clock,
                    cell.value,
                )
            )
        return (plan.widths, cells, pins, vcd)

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
        block = self._member_block.get(component)
        if block is not None:
            if block not in self._blocks_defaulted:
                self._blocks_defaulted.add(block)
                self.engine.block_default_state(block)
            return True
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

        # Read in the engine without a Python call (engine.get() reads the _nid of the port)
        def set_value_of(port: Port, value: Any) -> None:
            port.set_value(value)

        namespace: dict[str, Any] = {
            "_value": property(engine.get, set_raw),
            "value": property(engine.get, set_value_of),
        }
        if driven:
            # Port.value = x calls set_value(), the engine's for a port it drives
            namespace["value"] = property(engine.get, engine.put)
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

    def close(
        self,
    ) -> tuple[list[tuple[int, int, Port, Any]], dict[int, int], int, list[Callable[[], None]]]:
        """
        Give the ports back to Python. Returns the events in the order of the heap as
        (time, seq, port, value), the seq of the latest event of each port (by id()),
        the time, and what to call when the Python engine has the events: the cells of a
        block that wait for a settle make their events.
        """
        events, latest, clocks = self.engine.export()
        block_states = [self.engine.export_block(number) for number in range(len(self.blocks))]
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
        after: list[Callable[[], None]] = []
        for plan, states in zip(self.blocks, block_states, strict=True):
            after.extend(_restore_block(plan, states))
        ports = self.ports
        return (
            [(time, seq, ports[nid], value) for time, seq, nid, value in events],
            {id(ports[nid]): seq for nid, seq in enumerate(latest) if seq is not None},
            self.engine.time,
            after,
        )


def _word_of(ports: list[Port]) -> tuple[int, int]:
    """The bits and the undefined bits of the values of ports"""
    bits = undefined = 0
    for number, port in enumerate(ports):
        value = port._value
        if value == 1:
            bits |= 1 << number
        elif value != 0:
            undefined |= 1 << number
    return bits, undefined


def _restore_block(
    plan: _BlockPlan, states: list[tuple[tuple[int, int] | None, Any, bool]]
) -> list[Callable[[], None]]:
    """
    The state of the cells of a block in Python, from the values of their ports (back in
    Python) and the state of the engine. Returns what the cells that wait for a settle do
    then: a flip-flop sets its new output, a combinational cell updates.
    """
    after: list[Callable[[], None]] = []
    for cell, (q, clock, waiting) in zip(plan.cells, states, strict=True):
        component = cell.component
        if isinstance(component, functional.FunctionalCell):
            for name, word in component._inputs.items():
                word[0], word[1] = _word_of(component._bits[name])
            for name in component._outputs:
                component._outputs[name] = _word_of(component._bits[name])
            for name, word_output in component._word_outputs.items():
                bits, undefined = component._outputs[name]  # type: ignore[misc]
                word_output._value = bits | (undefined << len(component._bits[name]))
            if isinstance(component, functional._Register):
                component._old_clock = clock
                if q is not None:
                    component._q = q
                    if waiting:
                        after.append(functools.partial(component.write, "Q", q))
            elif waiting:
                after.append(component.update)
        elif cell.op == 1:
            if hasattr(component, "_old_C_level"):
                component._old_C_level = clock  # type: ignore[attr-defined]
            if waiting and cell.stateful and q is not None:
                code: VALUE_TYPE = "X" if q[1] & 1 else q[0] & 1
                output = component.outports()[0]
                after.append(functools.partial(output.set_value, code))
            elif waiting:
                after.append(component.update)
        elif waiting:
            after.append(component.default_state)
    return after
