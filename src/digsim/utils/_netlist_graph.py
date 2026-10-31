# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""
A netlist module as a graph to draw: its cells and ports as nodes, and the wires between
the ports of the nodes (pins), each with the bits (nets) it carries
"""

from __future__ import annotations

import dataclasses

from ._yosys_netlist import NET_TYPE, Nets, YosysCell, YosysPort


@dataclasses.dataclass(frozen=True)
class Pin:
    """A pin of a node, by the name of the node and of its port"""

    node: str
    port: str


@dataclasses.dataclass
class NetlistGraph:
    """
    The nodes of a netlist: its input ports (left), its output and inout ports (right)
    and its cells, by node name (see port_node() and cell_node()). The wires, from a pin
    to a pin, with the nets of their bits in the order of the bits of the sink port. The
    sink pins that all bits of are constants, with the constant as text.
    """

    inputs: list[str]
    outputs: list[str]
    cells: list[str]
    wires: dict[tuple[Pin, Pin], list[NET_TYPE]]
    constants: dict[Pin, str]


def port_node(name: str, is_input: bool) -> str:
    """The node of a module port"""
    return f"{'in' if is_input else 'out'}:{name}"


def cell_node(name: str) -> str:
    """The node of a cell"""
    return f"cell:{name}"


def constant_text(bits: list[NET_TYPE]) -> str:
    """A constant, lowest bit first: like 0 or 1, 4'hA, or 4'bx01x with undefined bits"""
    text = "".join(str(bit).lower() for bit in reversed(bits))
    if len(bits) == 1:
        return text
    if all(bit in ("0", "1") for bit in bits):
        return f"{len(bits)}'h{int(text, 2):X}"
    return f"{len(bits)}'b{text}"


def netlist_graph(
    ports: dict[str, YosysPort], cells: dict[str, YosysCell], nets: Nets
) -> NetlistGraph:
    """
    The nodes and wires of a module: its ports, the cells to draw, and its nets (see
    YosysModule.get_nets()). The wires to and from other cells are left out.
    """

    def source_pin(net: NET_TYPE) -> Pin | None:
        source = nets.source.get(net)
        if source is None:
            return None
        if source.cell is None:
            is_input = ports[source.name].direction == "input"
            return Pin(port_node(source.name, is_input), source.name)
        if source.cell not in cells:
            return None
        return Pin(cell_node(source.cell), source.name)

    def width(pin: Pin) -> int:
        kind, _, name = pin.node.partition(":")
        if kind == "cell":
            return len(cells[name].connections[pin.port])
        return len(ports[name].bits)

    bits: dict[tuple[Pin, Pin], dict[int, NET_TYPE]] = {}
    constant_bits: dict[Pin, dict[int, NET_TYPE]] = {}
    for net, sinks in nets.sinks.items():
        source = source_pin(net)
        for sink in sinks:
            if sink.cell is not None and sink.cell not in cells:
                continue
            if sink.cell is None:
                sink_pin = Pin(port_node(sink.name, False), sink.name)
            else:
                sink_pin = Pin(cell_node(sink.cell), sink.name)
            bit = sink.bit_index or 0
            if not isinstance(net, int):
                constant_bits.setdefault(sink_pin, {})[bit] = net
            elif source is not None:
                bits.setdefault((source, sink_pin), {})[bit] = net
    # The cells that drive an inout port
    for net, drivers in nets.inout_drivers.items():
        port = nets.source[net]
        sink_pin = Pin(port_node(port.name, False), port.name)
        for driver in drivers:
            assert driver.cell is not None
            if driver.cell not in cells:
                continue
            source = Pin(cell_node(driver.cell), driver.name)
            bits.setdefault((source, sink_pin), {})[port.bit_index or 0] = net
    constants: dict[Pin, str] = {}
    for pin, pin_bits in constant_bits.items():
        pin_width = width(pin)
        if len(pin_bits) == pin_width:
            constants[pin] = constant_text([pin_bits[bit] for bit in range(pin_width)])
    return NetlistGraph(
        inputs=[
            port_node(name, True) for name, port in ports.items() if port.direction == "input"
        ],
        outputs=[
            port_node(name, False) for name, port in ports.items() if port.direction != "input"
        ],
        cells=[cell_node(name) for name in cells],
        wires={
            key: [wire_bits[bit] for bit in sorted(wire_bits)] for key, wire_bits in bits.items()
        },
        constants=constants,
    )
