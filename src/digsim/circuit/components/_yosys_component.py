# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""
Module with classes to create a yosys component
from a yosys json netlist.
"""

from __future__ import annotations

import hashlib
import json
import threading
from collections import OrderedDict
from collections.abc import Iterable, Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import TYPE_CHECKING, Any, NamedTuple

import digsim.circuit.components._yosys_atoms
from digsim.synth import Synthesis
from digsim.utils import NetPort, Nets, YosysCell, YosysModule, YosysNetlist
from digsim.utils._yosys_netlist import NET_TYPE

from ._static_level import GND, VDD
from ._yosys_functional import (
    FUNCTIONAL_CELLS,
    IGNORED_CELLS,
    FunctionalCell,
    group_comparisons,
)
from .atoms import (
    VALUE_TYPE,
    Component,
    DigsimException,
    MultiComponent,
    Parameter,
    ParameterValue,
    Port,
    PortInOut,
    PortMultiBitWire,
)


if TYPE_CHECKING:
    from digsim.circuit import Circuit


class YosysComponentException(DigsimException):
    """Yosys component exception class"""


# Flip-flops on the implicit global clock, from formal Verilog like always @($global_clock)
GLOBAL_CLOCK_CELLS = {"$ff", "$_FF_"}


class YosysVariant(NamedTuple):
    """
    How a Verilog file is synthesized for a component: into functional blocks or gates,
    and with which parameters of its module ("NAME=VALUE,...", see YosysComponent)
    """

    functional: bool = False
    parameters: str = ""


def parameter_dict(parameters: str | Mapping[str, int] | None) -> dict[str, int]:
    """
    Parameters by name, from a dict or from "NAME=VALUE,..." (a value like 8, -1 or 0xff)

    Raises:
        YosysComponentException: If the text can't be read.
    """
    if parameters is None:
        return {}
    if not isinstance(parameters, str):
        for name, value in parameters.items():
            if not isinstance(value, int):
                raise YosysComponentException(f"The value of parameter '{name}' is not an int")
        return {name: int(value) for name, value in parameters.items()}
    values: dict[str, int] = {}
    for item in parameters.split(","):
        if not item.strip():
            continue
        name, equals, text = item.partition("=")
        try:
            if not equals:
                raise ValueError
            values[name.strip()] = int(text.strip(), 0)
        except ValueError:
            raise YosysComponentException(f"Not a parameter: '{item.strip()}'") from None
    return values


def parameter_text(parameters: Mapping[str, int]) -> str:
    """Parameters as "NAME=VALUE,...", sorted by name"""
    return ",".join(f"{name}={parameters[name]}" for name in sorted(parameters))


class _NetlistCache:
    """
    The netlists of the last Verilog files synthesized, as JSON text, by the file and its
    contents: undo and redo build the components again, and need not run Yosys for that
    """

    SIZE = 8

    def __init__(self) -> None:
        self._netlists: OrderedDict[tuple[str, str, YosysVariant], str] = OrderedDict()
        # The GUI synthesizes in a thread of its own
        self._lock = threading.Lock()

    @staticmethod
    def key(path: str, variant: YosysVariant) -> tuple[str, str, YosysVariant]:
        """The key of a file: its path, a hash of its contents, and how it is synthesized"""
        resolved = Path(path).resolve()
        digest = hashlib.sha256(resolved.read_bytes()).hexdigest()
        return str(resolved), digest, variant

    def get(self, key: tuple[str, str, YosysVariant]) -> dict[str, Any] | None:
        """The netlist, None if it isn't in the cache"""
        with self._lock:
            netlist_json = self._netlists.get(key)
            if netlist_json is None:
                return None
            self._netlists.move_to_end(key)
        return json.loads(netlist_json)

    def put(self, key: tuple[str, str, YosysVariant], netlist_dict: dict[str, Any]) -> None:
        """Add a netlist, the oldest one goes when the cache is full"""
        netlist_json = json.dumps(netlist_dict)
        with self._lock:
            self._netlists[key] = netlist_json
            self._netlists.move_to_end(key)
            while len(self._netlists) > self.SIZE:
                self._netlists.popitem(last=False)

    def clear(self) -> None:
        """Remove all netlists"""
        with self._lock:
            self._netlists.clear()


_netlist_cache = _NetlistCache()

# The netlists that the components being built use instead of their files, by file and
# variant, in the order of the components (see YosysComponent.given_netlists())
_given_netlists: ContextVar[dict[tuple[str, YosysVariant], list[YosysNetlist]] | None] = (
    ContextVar("_given_netlists", default=None)
)


def _given_key(path: str | Path, variant: YosysVariant) -> tuple[str, YosysVariant]:
    return str(Path(path).resolve()), variant


class SignalPort(PortMultiBitWire):
    """
    A named signal of a Yosys component, a wire or register of the Verilog (see the
    'signals' argument of YosysComponent). Its bits are wired from the nets of the signal,
    and it is in the VCD file like a port.
    """

    def __init__(self, parent: Component, name: str, width: int) -> None:
        super().__init__(parent, name, width, output=True)


class StatePort(SignalPort):
    """
    The names of the values of a signal, like the states of a state machine, as a port
    next to the signal's own port: "state_name" for "state". It is in the VCD file as
    text, the name of its value, and the signal as a number.
    """

    def __init__(self, parent: Component, name: str, width: int, names: dict[int, str]) -> None:
        self._names = names
        super().__init__(parent, name, width)

    @property
    def names(self) -> dict[int, str]:
        """The names of the values"""
        return self._names

    def state(self) -> str:
        """The name of the value, the value as a number if it has no name, or X"""
        value = self.value
        if not isinstance(value, int):
            return value
        return self._names.get(value, str(value))

    def vcd_text(self) -> str:
        """The text in the VCD file"""
        return self.state()


class _Signals(Component):
    """The named signals of a Yosys component, as ports"""


class YosysComponent(MultiComponent):
    """
    A component built from a Verilog file or a Yosys JSON netlist, named after its module.

    Ports:
        The ports of the Verilog module, with the same names and widths. An inout port is
            a PortInOut, wire it both ways to another inout port.

    Args:
        circuit: The circuit to add the component to.
        path: A Verilog file (.v, or SystemVerilog .sv) or Yosys netlist (.json) with one
            module, or None to create the component later with create_from_netlist().
        functional: Synthesize a Verilog file into functional blocks, like adders and
            multiplexers, instead of gates, which simulates faster. A netlist is used as
            it is.
        signals: Make the named signals of the netlist (the wires and registers of the
            Verilog) readable with signal(), and write them to the VCD file. It makes the
            simulation slower. A signal with names for its values (an enum, or a signal
            with the width of at least two parameters) is written as its value and, in
            "<signal>_name", as the names, see state().
        states: More signals (with signals=True) to write with the names of their values:
            signals of one bit, or with one name. A list, or names separated by commas.
        parameters: Values for parameters of the Verilog module instead of their
            defaults: a dict like {"WIDTH": 16}, or "WIDTH=16,DEPTH=4". The values are
            integers. A netlist file has no parameters.

    Raises:
        YosysComponentException: If parameters are given for a netlist file, or can't be
            read.
    """

    def __init__(
        self,
        circuit: Circuit,
        path: str | Path | None = None,
        *,
        functional: bool = False,
        signals: bool = False,
        states: str | list[str] | None = None,
        parameters: str | Mapping[str, int] | None = None,
    ) -> None:
        if path is not None and not str(path):
            raise YosysComponentException("A Yosys component needs a Verilog or netlist file")
        super().__init__(circuit)
        self._path = str(path) if path is not None else None
        self._functional = functional
        self._module_parameters = self._checked_parameters(parameters)
        self._signals = signals
        self._states = self._state_list(states)
        # The settings that can be changed later, see reconfigure()
        self.parameter_set("functional", functional)
        self.parameter_set("signals", signals)
        self.parameter_set("states", ",".join(self._states))
        self._signals_comp: _Signals | None = None
        # The ports with the names of the values of signals, by signal (see StatePort)
        self._state_ports: dict[str, StatePort] = {}
        self._netlist_module: YosysModule | None = None
        self._module_name = ""
        # The cells of the netlist, as components
        self._gates_comp = MultiComponent(self._circuit, "gates")
        self.add(self._gates_comp)

        if path is not None:
            self._load_file()

    @staticmethod
    def _is_verilog(path: str) -> bool:
        return path.endswith((".v", ".sv"))

    def _checked_parameters(self, parameters: str | Mapping[str, int] | None) -> str:
        """The parameters as text, if the component can have them"""
        text = parameter_text(parameter_dict(parameters))
        if text and self._path is not None and not self._is_verilog(self._path):
            raise YosysComponentException(
                f"'{self._path}' is not a Verilog file, it has no parameters"
            )
        return text

    def set_parameters(self, parameters: str | Mapping[str, int] | None) -> None:
        """
        Change the parameters of the Verilog module, without building the component
        again: for a netlist synthesized with them, that reload_from_netlist() builds it
        from next (or a circuit built again from the settings of its components).

        Raises:
            YosysComponentException: If the parameters can't be read, or the component is
                made from a netlist file.
        """
        self._module_parameters = self._checked_parameters(parameters)

    @staticmethod
    def _state_list(states: str | list[str] | None) -> list[str]:
        """The signals with state names, from a list or names separated by commas"""
        if isinstance(states, str):
            return [state.strip() for state in states.split(",") if state.strip()]
        return list(states or [])

    @staticmethod
    def _first_module(netlist_object: YosysNetlist) -> tuple[str, YosysModule]:
        return next(iter(netlist_object.get_modules().items()))

    def create_from_netlist(self, netlist_object: YosysNetlist) -> None:
        """Create component from netlist object"""
        module_name, netlist_module = self._first_module(netlist_object)
        self._netlist_module = netlist_module
        self._module_name = module_name

        # Set Name
        self.set_name(module_name)
        self.set_display_name(module_name)
        # Add External Ports
        for portname, port_dict in netlist_module.ports.items():
            external_port: Port
            if port_dict.is_inout:
                external_port = PortInOut(self, portname, width=len(port_dict.bits))
            else:
                external_port = PortMultiBitWire(
                    self, portname, width=len(port_dict.bits), output=port_dict.is_output
                )
            self.add_port(external_port)
        # Create component
        self._create_component()

    def reload_from_netlist(self, netlist_object: YosysNetlist) -> None:
        """Reload netlist from netlist object"""
        _, reload_module = self._first_module(netlist_object)

        if self._netlist_module is None or not self._netlist_module.is_same_interface(
            reload_module
        ):
            raise YosysComponentException("Yosys component interface differs")
        # Checked before the component is taken apart, so that it stays as it was
        self._check_module(reload_module, self._signals, self._states)
        self._rebuild(reload_module)

    def _rebuild(self, module: YosysModule) -> None:
        """Build the component again from a module with the same ports"""
        # Disconnect ports
        self._disconnect_external_ports()
        # Remove yosys atoms, and the named signals
        self._gates_comp.remove_all_components()
        if self._signals_comp is not None:
            self._circuit.delete_component(self._signals_comp)
            self._components.remove(self._signals_comp)
            self._signals_comp = None
        # Setup netlist
        self._netlist_module = module
        # Create component
        self._create_component()

    def reconfigure(self) -> None:
        """
        Build the component again with the changed settings ('functional', 'signals' and
        'states'). A Verilog file is synthesized again when 'functional' changes.

        Raises:
            YosysComponentException: If a signal in 'states' is not in the netlist, or the
                ports of the file have changed (reload it first). The component and its
                settings are as before.
            SynthesisException: If the Verilog can't be synthesized.
        """
        functional = bool(self.parameter_get("functional"))
        signals = bool(self.parameter_get("signals"))
        states = self._state_list(self.parameter_get("states"))
        if (functional, signals, states) == (self._functional, self._signals, self._states):
            return
        try:
            module = self._module()
            path = self._path
            if functional != self._functional and path is not None and self._is_verilog(path):
                netlist = YosysNetlist(
                    **self.synthesize_file(
                        path, functional, parameters=parameter_dict(self._module_parameters)
                    )
                )
                _, module = self._first_module(netlist)
                if not module.is_same_interface(self._module()):
                    raise YosysComponentException(
                        f"The ports of '{path}' have changed, reload the component first"
                    )
            self._check_module(module, signals, states)
        except (DigsimException, OSError):
            # The settings as they were
            self.parameter_set("functional", self._functional)
            self.parameter_set("signals", self._signals)
            self.parameter_set("states", ",".join(self._states))
            raise
        self._functional, self._signals, self._states = functional, signals, states
        self._rebuild(module)

    def netlist(self) -> YosysNetlist:
        """The netlist that the component is built from now"""
        return YosysNetlist(modules={self._module_name: self._module()})

    @staticmethod
    @contextmanager
    def given_netlists(
        netlists: Iterable[tuple[str | Path, YosysVariant, YosysNetlist]],
    ) -> Iterator[None]:
        """
        Components built in the context use given netlists instead of reading their files,
        like when a circuit is built again: (file, variant, netlist) for each component,
        in the order that the components are built. A component of a file that has no
        netlist left reads its file.
        """
        given: dict[tuple[str, YosysVariant], list[YosysNetlist]] = {}
        for path, variant, netlist in netlists:
            given.setdefault(_given_key(path, variant), []).append(netlist)
        token = _given_netlists.set(given)
        try:
            yield
        finally:
            _given_netlists.reset(token)

    def _module(self) -> YosysModule:
        if self._netlist_module is None:
            raise YosysComponentException("No netlist loaded")
        return self._netlist_module

    def _bus_port(self, portname: str) -> PortMultiBitWire | PortInOut:
        port = self.port(portname)
        if not isinstance(port, (PortMultiBitWire, PortInOut)):
            raise YosysComponentException(f"Port '{portname}' is not a bus port")
        return port

    @staticmethod
    def _unsupported(cell: YosysCell) -> YosysComponentException:
        """The error for a cell that can't be simulated"""
        if cell.type in GLOBAL_CLOCK_CELLS:
            return YosysComponentException(
                f"Unsupported Yosys cell '{cell.type}': a register on the global clock "
                "($global_clock), DigSim has no global clock"
            )
        return YosysComponentException(f"Unsupported Yosys cell '{cell.type}'")

    @staticmethod
    def _supported(cell: YosysCell) -> bool:
        """True if a cell can be simulated (or is ignored)"""
        if cell.type in IGNORED_CELLS or cell.type in FUNCTIONAL_CELLS:
            return True
        if cell.is_gate:
            atoms = digsim.circuit.components._yosys_atoms
            return getattr(atoms, cell.component_type(), None) is not None
        return False

    @classmethod
    def _check_module(cls, module: YosysModule, signals: bool, states: list[str]) -> None:
        """
        Check that a component can be built from a module, with these settings

        Raises:
            YosysComponentException: If a cell can't be simulated, or a signal in 'states'
                is not in the module.
        """
        for cell in group_comparisons(module.cells).values():
            if not cls._supported(cell):
                raise cls._unsupported(cell)
        if signals:
            names = module.signal_names()
            for state in states:
                if state not in names:
                    raise YosysComponentException(f"No signal '{state}' for state names")

    def check_netlist(self, netlist_object: YosysNetlist) -> None:
        """
        Check that the component can be built from a netlist (see reload_from_netlist),
        before it is taken apart.

        Raises:
            YosysComponentException: If a cell can't be simulated, or a signal in the
                'states' argument is not in the netlist.
        """
        _, module = self._first_module(netlist_object)
        self._check_module(module, self._signals, self._states)

    def _create_cells(self, cells: dict[str, YosysCell]) -> dict[str, Component]:
        """Create cells in component"""
        components_dict: dict[str, Component] = {}
        for cellname, cell in cells.items():
            if cell.type in IGNORED_CELLS:
                continue
            name = cell.component_name(cellname)
            component: Component
            if cell.is_gate:
                component_class = getattr(
                    digsim.circuit.components._yosys_atoms, cell.component_type(), None
                )
                if component_class is None:
                    raise self._unsupported(cell)
                component = component_class(self._circuit, name=name)
            elif cell.type in FUNCTIONAL_CELLS:
                component = FUNCTIONAL_CELLS[cell.type](self._circuit, name, cell)
            else:
                raise self._unsupported(cell)
            self._gates_comp.add(component)
            components_dict[cellname] = component

        vdd = VDD(self._circuit)
        self._gates_comp.add(vdd)
        components_dict["VDD"] = vdd
        gnd = GND(self._circuit)
        self._gates_comp.add(gnd)
        components_dict["GND"] = gnd

        return components_dict

    @staticmethod
    def _cell_port(component: Component, net_port: NetPort) -> Port:
        """The port of a cell on a net: a gate port, or one bit of a functional cell port"""
        if isinstance(component, FunctionalCell):
            assert net_port.bit_index is not None
            return component.cell_port(net_port.name, net_port.bit_index)
        return component.port(net_port.name)

    @staticmethod
    def _link_functional_cells(
        components_dict: dict[str, Component], cells: dict[str, YosysCell], nets: Nets
    ) -> set[tuple[str, str, int]]:
        """
        Connect the outputs of functional cells to the inputs of functional cells as words,
        a part of an input for each run of bits from the same output. Returns the input
        bits that are connected, (cell, port, bit).
        """
        linked: set[tuple[str, str, int]] = set()
        for cellname, cell in cells.items():
            component = components_dict.get(cellname)
            if not isinstance(component, FunctionalCell):
                continue
            for port, bits in cell.connections.items():
                if cell.port_directions.get(port) != "input":
                    continue
                # Runs of bits from consecutive bits of the same output
                run: tuple[FunctionalCell, str, int, int, int] | None = None
                runs: list[tuple[FunctionalCell, str, int, int, int]] = []
                for bit, net in enumerate(bits):
                    source = nets.source.get(net)
                    source_comp = (
                        None
                        if source is None or source.cell is None
                        else components_dict[source.cell]
                    )
                    if source is None or not isinstance(source_comp, FunctionalCell):
                        run = None
                        continue
                    assert source.bit_index is not None
                    if (
                        run is not None
                        and run[0] is source_comp
                        and run[1] == source.name
                        and run[3] + run[4] == source.bit_index
                    ):
                        run = (run[0], run[1], run[2], run[3], run[4] + 1)
                        runs[-1] = run
                    else:
                        run = (source_comp, source.name, bit, source.bit_index, 1)
                        runs.append(run)
                    linked.add((cellname, port, bit))
                for source_comp, output, offset, start, width in runs:
                    source_comp.link(output, start, component, port, offset, width)
        return linked

    def _connect_sinks(
        self,
        components_dict: dict[str, Component],
        src_comp_port: Port,
        sinks: list[NetPort],
        linked: set[tuple[str, str, int]] | None = None,
    ) -> None:
        """Connect a source port to multiple sinks, not the ones that are linked as words"""
        for sink_port in sinks:
            if linked and (sink_port.cell, sink_port.name, sink_port.bit_index) in linked:
                continue
            if sink_port.cell is None:
                # Connect cell output to module top
                assert sink_port.bit_index is not None
                dst_port = self._bus_port(sink_port.name).get_bit(sink_port.bit_index)
                src_comp_port.wire = dst_port
            else:
                # Connect cell output to cell input
                dst_comp = components_dict[sink_port.cell]
                src_comp_port.wire = self._cell_port(dst_comp, sink_port)

    def _connect_cells(
        self,
        components_dict: dict[str, Component],
        nets: Nets,
        linked: set[tuple[str, str, int]],
    ) -> None:
        """Connect all cells"""
        for net, source in nets.source.items():
            if source.cell is None:
                # Only connect cells here
                continue
            src_comp = components_dict[source.cell]
            self._connect_sinks(
                components_dict,
                self._cell_port(src_comp, source),
                nets.sinks.get(net, []),
                linked,
            )

        gnd_sinks = nets.sinks.get("0", [])
        self._connect_sinks(components_dict, components_dict["GND"].port("O"), gnd_sinks)
        vdd_sinks = nets.sinks.get("1", [])
        self._connect_sinks(components_dict, components_dict["VDD"].port("O"), vdd_sinks)

    def _connect_external_input(self, components_dict: dict[str, Component], nets: Nets) -> None:
        """
        Connect each bit of the input and inout ports to the cell inputs and module outputs
        it drives
        """
        for portname, port in self._module().ports.items():
            if port.is_output:
                continue
            bus_port = self._bus_port(portname)
            for bit_index, net in enumerate(port.bits):
                if port.is_inout and not isinstance(net, int):
                    # A constant bit, the component drives it (see _connect_inout_drivers)
                    continue
                self._connect_sinks(
                    components_dict, bus_port.get_bit(bit_index), nets.sinks.get(net, [])
                )

    def _connect_inout_drivers(self, components_dict: dict[str, Component], nets: Nets) -> None:
        """
        Connect the cell outputs on the nets of the inout ports, and the constant bits, to
        the bits that the ports drive. An inout port that drives only from tristate cells
        (or not at all) is a tristate port.
        """
        for portname, port in self._module().ports.items():
            if not port.is_inout:
                continue
            inout_port = self._bus_port(portname)
            assert isinstance(inout_port, PortInOut)
            tristate = True
            for bit_index, net in enumerate(port.bits):
                drive_bit = inout_port.get_drive_bit(bit_index)
                if net in ("0", "1"):
                    components_dict["GND" if net == "0" else "VDD"].port("O").wire = drive_bit
                for driver in nets.inout_drivers.get(net, []):
                    assert driver.cell is not None
                    self._cell_port(components_dict[driver.cell], driver).wire = drive_bit
                tristate = tristate and all(d.is_tristate() for d in drive_bit.get_drivers())
            inout_port.set_tristate(tristate)

    def _create_component(self) -> None:
        """Create yosys component"""
        module = self._module()
        # Comparisons of the same nets with constants are simulated as one cell
        cells = group_comparisons(module.cells)
        nets = YosysModule(ports=module.ports, cells=cells).get_nets()
        # Create cells
        components_dict = self._create_cells(cells)
        # Connect cells, functional cells to each other as words
        linked = self._link_functional_cells(components_dict, cells, nets)
        self._connect_cells(components_dict, nets, linked)
        # Connect external input ports, and the drivers of the inout ports
        self._connect_external_input(components_dict, nets)
        self._connect_inout_drivers(components_dict, nets)
        # An output driven only by tristate cells is a tristate output (it can share a wire)
        for portname, port in self._module().ports.items():
            if port.is_output:
                bus_port = self._bus_port(portname)
                drivers = [bus_port.get_bit(bit).get_drivers() for bit in range(bus_port.width)]
                bus_port.set_tristate(
                    all(
                        bit_drivers and all(d.is_tristate() for d in bit_drivers)
                        for bit_drivers in drivers
                    )
                )
        if self._signals:
            self._create_signals(components_dict, nets)

    def _driver(
        self, components_dict: dict[str, Component], nets: Nets, net: NET_TYPE
    ) -> Port | None:
        """The port that drives a net, None if nothing does (like an undefined bit)"""
        if net in ("0", "1"):
            return components_dict["GND" if net == "0" else "VDD"].port("O")
        source = nets.source.get(net)
        if source is None:
            return None
        if source.cell is None:
            assert source.bit_index is not None
            return self._bus_port(source.name).get_bit(source.bit_index)
        return self._cell_port(components_dict[source.cell], source)

    def _create_signals(self, components_dict: dict[str, Component], nets: Nets) -> None:
        """The named signals, as ports wired from their nets"""
        module = self._module()
        names = module.signal_names()
        for state in self._states:
            if state not in names:
                raise YosysComponentException(f"No signal '{state}' for state names")
        signals_comp = _Signals(self._circuit, "signals")
        self.add(signals_comp)
        self._signals_comp = signals_comp
        self._state_ports = {}
        named = set(self._module_state_signals(module)) | set(self._states)
        taken = set(names)
        for name in names:
            netname = module.netnames[name]
            width = len(netname.bits)
            value_names = netname.enum_names()
            if name in named:
                value_names = module.state_names(name)
            ports: list[SignalPort] = [SignalPort(signals_comp, name, width)]
            if value_names or name in named:
                # "state_name" for "state", unless the design has a signal with that name
                state_name = f"{name}_name"
                while state_name in taken:
                    state_name += "_"
                taken.add(state_name)
                state_port = StatePort(signals_comp, state_name, width, value_names)
                self._state_ports[name] = state_port
                ports.append(state_port)
            for port in ports:
                signals_comp.add_port(port)
                for bit, net in enumerate(netname.bits):
                    driver = self._driver(components_dict, nets, net)
                    if driver is not None:
                        driver.wire = port.get_bit(bit)

    @property
    def source_file(self) -> str | None:
        """The Verilog or netlist file of the component, None if it was made from a netlist"""
        return self._path

    @property
    def functional(self) -> bool:
        """True if the Verilog is synthesized into functional blocks"""
        return self._functional

    @property
    def parameters(self) -> dict[str, int]:
        """The parameters of the Verilog module that have other values than their defaults"""
        return parameter_dict(self._module_parameters)

    @property
    def variant(self) -> YosysVariant:
        """How the Verilog is synthesized: 'functional' and the parameters"""
        return YosysVariant(self._functional, self._module_parameters)

    @staticmethod
    def netlist_interface(netlist_object: YosysNetlist) -> dict[str, tuple[str, int]]:
        """
        The ports of the (first) module of a netlist: name to (direction, width), the
        direction "input", "output" or "inout"
        """
        _, module = YosysComponent._first_module(netlist_object)
        return {name: (port.direction, len(port.bits)) for name, port in module.ports.items()}

    def interface(self) -> dict[str, tuple[str, int]]:
        """The ports of the component: name to (direction, width), see netlist_interface()"""
        return {
            name: (port.direction, len(port.bits)) for name, port in self._module().ports.items()
        }

    def signal_names(self) -> list[str]:
        """
        The named signals of the netlist, the wires and registers of the Verilog, like
        "PC" or "ALU.OUT" (from the ALU submodule)
        """
        return self._module().signal_names()

    def _signal_port(self, name: str) -> SignalPort:
        if self._signals_comp is None:
            raise YosysComponentException(
                f"The signals of '{self.name()}' are not available, create it with signals=True"
            )
        if name not in self._signals_comp.__dict__:
            raise YosysComponentException(f"No signal '{name}' in '{self.name()}'")
        port = self._signals_comp.port(name)
        assert isinstance(port, SignalPort)
        return port

    def signal(self, name: str) -> VALUE_TYPE:
        """
        The value of a named signal, see signal_names().

        Raises:
            YosysComponentException: If the component was created without signals=True,
                or it has no signal with the name.
        """
        return self._signal_port(name).value

    def state(self, name: str) -> str:
        """
        The name of the value of a signal with named values (see the 'states' argument),
        like the state of a state machine. A value without a name is returned as a number.

        Raises:
            YosysComponentException: If the component was created without signals=True,
                or the signal has no names for its values.
        """
        self._signal_port(name)
        port = self._state_ports.get(name)
        if port is None:
            raise YosysComponentException(f"The signal '{name}' has no names for its values")
        return port.state()

    @staticmethod
    def _module_state_signals(module: YosysModule) -> dict[str, tuple[list[str], bool]]:
        """
        The signals of a module that are written with the names of their values: signal
        to (names, is an enum). Signals of one bit, and with fewer than two names, are left
        out (except the ones in the 'states' argument).
        """
        signals: dict[str, tuple[list[str], bool]] = {}
        for name in module.signal_names():
            netname = module.netnames[name]
            names = module.state_names(name)
            if len(netname.bits) > 1 and len(names) >= 2:
                ordered = [names[value] for value in sorted(names)]
                signals[name] = (ordered, bool(netname.enum_names()))
        return signals

    def _file_path(self) -> str:
        """The Verilog or netlist file of the component"""
        if self._path is None:
            raise YosysComponentException(
                f"Yosys component '{self.name()}' has no file, it was created from a netlist"
            )
        return self._path

    @staticmethod
    def synthesize_file(
        path: str | Path,
        functional: bool = False,
        log: list[str] | None = None,
        cached: bool = True,
        top: str | None = None,
        parameters: Mapping[str, int] | None = None,
    ) -> dict[str, Any]:
        """
        Synthesize a Verilog file with one module into a netlist dict, as a YosysComponent
        does. The last netlists are kept, by the contents of the file, and a component
        made from the same file uses its netlist.

        Args:
            path: The Verilog file (.v or .sv).
            functional: Synthesize into functional blocks, see YosysComponent.
            log: A list to add the Yosys log to.
            cached: Use the netlist of the last synthesis of the same file contents. With
                False Yosys always runs (to get its log), and the netlist is kept.
            top: The module of the file, if it is known. Else the file is checked to have
                one module.
            parameters: Values for parameters of the module, see YosysComponent.

        Raises:
            SynthesisException: If Yosys reports an error, like a syntax error.
            YosysComponentException: If the file has more than one module.
            OSError: If the file can't be read.
        """
        path = str(path)
        parameters = dict(parameters or {})
        key = _netlist_cache.key(path, YosysVariant(functional, parameter_text(parameters)))
        if cached:
            netlist_dict = _netlist_cache.get(key)
            if netlist_dict is not None:
                return netlist_dict
        yosys_log = log if log is not None else []
        if top is None:
            modules = Synthesis.list_modules(path, log=yosys_log)
            if len(modules) != 1:
                raise YosysComponentException(
                    "Current only one module per verilog file is supported"
                )
            top = modules[0]
        synthesis = Synthesis(path, top, functional=functional, parameters=parameters)
        try:
            netlist_dict = synthesis.synth_to_dict(silent=True)
        finally:
            yosys_log.extend(synthesis.get_log())
        # Only when the file didn't change while Yosys read it (by a save, or another
        # program): the netlist is then of the contents the key has
        if _netlist_cache.key(path, key[2]) == key:
            _netlist_cache.put(key, netlist_dict)
        return netlist_dict

    def _synth_verilog(self, path: str) -> dict[str, Any]:
        """Synthesize verilog to netlist"""
        return self.synthesize_file(path, self._functional, parameters=self.parameters)

    def _load_netlist_dict(self) -> YosysNetlist:
        """Load yosys netlist dict"""
        path = self._file_path()
        given = _given_netlists.get()
        if given is not None:
            netlists = given.get(_given_key(path, self.variant))
            if netlists:
                return netlists.pop(0)
        try:
            if path.endswith(".json"):
                with open(path, encoding="utf-8") as json_file:
                    netlist_dict = json.load(json_file)
            elif self._is_verilog(path):
                netlist_dict = self._synth_verilog(path)
            else:
                raise YosysComponentException(f"Unknown file extension '{path}'")
            yosys_netlist = YosysNetlist(**netlist_dict)
        except ValueError as exc:
            # Malformed JSON, or JSON that is not a Yosys netlist (pydantic ValidationError)
            raise YosysComponentException(f"Not a Yosys netlist: '{path}'") from exc
        modules = yosys_netlist.get_modules()

        if len(modules) > 1:
            raise YosysComponentException("Only one module per file is supported")

        return yosys_netlist

    def _load_file(self) -> None:
        """Load yosys verilog/json-netlist file"""
        yosys_netlist = self._load_netlist_dict()
        self.create_from_netlist(yosys_netlist)

    def reload_file(self) -> None:
        """Reload yosys verilog/json-netlist file"""
        yosys_netlist = self._load_netlist_dict()
        self.reload_from_netlist(yosys_netlist)

    def _disconnect_external_ports(self) -> None:
        """Disconnect external ports before reload"""
        for port in self.ports:
            if isinstance(port, PortInOut):
                for bit_id in range(port.width):
                    port.get_bit(bit_id).remove_wires()
                    drive_bit = port.get_drive_bit(bit_id)
                    for driver in drive_bit.get_drivers():
                        driver.disconnect(drive_bit)
        for port in self.inports():
            bus_port = self._bus_port(port.name())
            for bit_id in range(bus_port.width):
                bus_port.get_bit(bit_id).remove_wires()
        for port in self.outports():
            bus_port = self._bus_port(port.name())
            for bit_id in range(bus_port.width):
                bus_port.get_bit(bit_id).set_driver(None)

    def settings_to_dict(self) -> dict[str, ParameterValue]:
        path = self.circuit.store_path(self._file_path())
        settings: dict[str, ParameterValue] = {"path": path}
        # Only when set, so that files without them still open in older versions
        if self._functional:
            settings["functional"] = True
        if self._signals:
            settings["signals"] = True
        if self._states:
            settings["states"] = ",".join(self._states)
        if self._module_parameters:
            settings["parameters"] = self._module_parameters
        return settings

    def get_reconfigurable_parameters(self) -> dict[str, Parameter]:
        parameters = super().get_reconfigurable_parameters()
        path = self._path or ""
        return {
            name: parameter
            for name, parameter in parameters.items()
            if path.lower().endswith(tuple(parameter.get("file_types", [""])))
        }

    @classmethod
    def get_parameters(cls) -> dict[str, Parameter]:
        return {
            "path": {
                "type": "path",
                "fileinfo": "Netlist or Verilog (*.json *.v *.sv)",
                "description": "Open a Verilog file or Yosys netlist",
                "new_verilog": True,
            },
            "functional": {
                "type": "bool",
                "default": False,
                "description": "Synthesize Verilog into functional blocks (faster)",
                "reconfigurable": True,
                # A netlist is not synthesized
                "file_types": [".v", ".sv"],
            },
            "signals": {
                "type": "bool",
                "default": False,
                "description": "Write all internal signals (wires and registers) to the VCD "
                "file, states also with their names (slower)",
                "reconfigurable": True,
            },
        }
