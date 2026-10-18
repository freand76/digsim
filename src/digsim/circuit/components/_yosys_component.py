# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""
Module with classes to create a yosys component
from a yosys json netlist.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import digsim.circuit.components._yosys_atoms
from digsim.synth import Synthesis
from digsim.utils import NetPort, Nets, YosysCell, YosysModule, YosysNetlist

from ._static_level import GND, VDD
from ._yosys_functional import (
    FUNCTIONAL_CELLS,
    IGNORED_CELLS,
    FunctionalCell,
    group_comparisons,
)
from .atoms import (
    Component,
    DigsimException,
    MultiComponent,
    Parameter,
    ParameterValue,
    Port,
    PortMultiBitWire,
)


if TYPE_CHECKING:
    from pathlib import Path

    from digsim.circuit import Circuit


class YosysComponentException(DigsimException):
    """Yosys component exception class"""


class YosysComponent(MultiComponent):
    """
    A component built from a Verilog file or a Yosys JSON netlist.

    Ports:
        The ports of the Verilog module, with the same names and widths.

    Args:
        circuit: The circuit to add the component to.
        name: The component name, the class name if not given.
        path: A Verilog file (.v) or Yosys netlist (.json) with one module, or None to
            create the component later with create_from_netlist().
        functional: Synthesize a Verilog file into functional blocks, like adders and
            multiplexers, instead of gates, which simulates faster. A netlist is used as
            it is.
    """

    def __init__(
        self,
        circuit: Circuit,
        path: str | Path | None = None,
        name: str | None = None,
        functional: bool = False,
    ) -> None:
        super().__init__(circuit, name)
        self._path = str(path) if path is not None else None
        self._functional = functional
        self._netlist_module: YosysModule | None = None
        # The cells of the netlist, as components
        self._gates_comp = MultiComponent(self._circuit, "gates")
        self.add(self._gates_comp)

        if path is not None:
            self._load_file()

    @staticmethod
    def _first_module(netlist_object: YosysNetlist) -> tuple[str, YosysModule]:
        return next(iter(netlist_object.get_modules().items()))

    def create_from_netlist(self, netlist_object: YosysNetlist) -> None:
        """Create component from netlist object"""
        module_name, netlist_module = self._first_module(netlist_object)
        self._netlist_module = netlist_module

        # Set Name
        self.set_name(module_name)
        self.set_display_name(module_name)
        # Add External Ports
        for portname, port_dict in netlist_module.ports.items():
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

        # Disconnect ports
        self._disconnect_external_ports()
        # Remove yosys atoms
        self._gates_comp.remove_all_components()
        # Setup netlist
        self._netlist_module = reload_module
        # Create component
        self._create_component()

    def _module(self) -> YosysModule:
        if self._netlist_module is None:
            raise YosysComponentException("No netlist loaded")
        return self._netlist_module

    def _bus_port(self, portname: str) -> PortMultiBitWire:
        port = self.port(portname)
        if not isinstance(port, PortMultiBitWire):
            raise YosysComponentException(f"Port '{portname}' is not a bus port")
        return port

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
                    raise YosysComponentException(f"Unsupported Yosys cell '{cell.type}'")
                component = component_class(self._circuit, name=name)
            elif cell.type in FUNCTIONAL_CELLS:
                component = FUNCTIONAL_CELLS[cell.type](self._circuit, name, cell)
            else:
                raise YosysComponentException(f"Unsupported Yosys cell '{cell.type}'")
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

    def _connect_sinks(
        self, components_dict: dict[str, Component], src_comp_port: Port, sinks: list[NetPort]
    ) -> None:
        """Connect a source port to multiple sinks"""
        for sink_port in sinks:
            if sink_port.cell is None:
                # Connect cell output to module top
                assert sink_port.bit_index is not None
                dst_port = self._bus_port(sink_port.name).get_bit(sink_port.bit_index)
                src_comp_port.wire = dst_port
            else:
                # Connect cell output to cell input
                dst_comp = components_dict[sink_port.cell]
                src_comp_port.wire = self._cell_port(dst_comp, sink_port)

    def _connect_cells(self, components_dict: dict[str, Component], nets: Nets) -> None:
        """Connect all cells"""
        for net, source in nets.source.items():
            if source.cell is None:
                # Only connect cells here
                continue
            src_comp = components_dict[source.cell]
            self._connect_sinks(
                components_dict, self._cell_port(src_comp, source), nets.sinks.get(net, [])
            )

        gnd_sinks = nets.sinks.get("0", [])
        self._connect_sinks(components_dict, components_dict["GND"].port("O"), gnd_sinks)
        vdd_sinks = nets.sinks.get("1", [])
        self._connect_sinks(components_dict, components_dict["VDD"].port("O"), vdd_sinks)

    def _connect_external_input(self, components_dict: dict[str, Component], nets: Nets) -> None:
        """Connect each bit of the input ports to the cell inputs and module outputs it drives"""
        for portname, port in self._module().ports.items():
            if port.is_output:
                continue
            bus_port = self._bus_port(portname)
            for bit_index, net in enumerate(port.bits):
                self._connect_sinks(
                    components_dict, bus_port.get_bit(bit_index), nets.sinks.get(net, [])
                )

    def _create_component(self) -> None:
        """Create yosys component"""
        module = self._module()
        # Comparisons of the same nets with constants are simulated as one cell
        cells = group_comparisons(module.cells)
        nets = YosysModule(ports=module.ports, cells=cells).get_nets()
        # Create cells
        components_dict = self._create_cells(cells)
        # Connect cells
        self._connect_cells(components_dict, nets)
        # Connect external input ports
        self._connect_external_input(components_dict, nets)

    def _file_path(self) -> str:
        """The Verilog or netlist file of the component"""
        if self._path is None:
            raise YosysComponentException(
                f"Yosys component '{self.name()}' has no file, it was created from a netlist"
            )
        return self._path

    def _synth_verilog(self, path: str) -> dict[str, Any]:
        """Synthesize verilog to netlist"""
        modules = Synthesis.list_modules(path)
        if len(modules) == 1:
            toplevel = modules[0]
        else:
            raise YosysComponentException("Current only one module per verilog file is supported")

        synthesis = Synthesis(path, toplevel, functional=self._functional)
        return synthesis.synth_to_dict(silent=True)

    def _load_netlist_dict(self) -> YosysNetlist:
        """Load yosys netlist dict"""
        path = self._file_path()
        try:
            if path.endswith(".json"):
                with open(path, encoding="utf-8") as json_file:
                    netlist_dict = json.load(json_file)
            elif path.endswith(".v"):
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
        if self._functional:
            # Only when set, so that files without it still open in older versions
            settings["functional"] = True
        return settings

    @classmethod
    def get_parameters(cls) -> dict[str, Parameter]:
        return {
            "path": {
                "type": "path",
                "fileinfo": "Yosys JSON Netlist (*.json);;Verilog File (*.v)",
                "description": "Select verilog file or Yosys json netlist",
            },
            "functional": {
                "type": "bool",
                "default": False,
                "description": "Synthesize Verilog into functional blocks (faster)",
            },
        }
