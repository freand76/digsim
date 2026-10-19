# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""The wires of the GUI and their names in the circuit file, without Qt so they can be tested"""

from digsim.circuit.components.atoms import Port


# A wire: (output port, input port), a connection. An input port has one driver, or
# several, then each has a wire of its own to it. A drawn wire can also be between two
# ports of the same kind, (start port, end port), that is no connection.
Wire = tuple[Port, Port]


def port_key(port: Port) -> str:
    """The name of a port in the circuit file, "component.port" """
    return f"{port.parent().name()}.{port.name()}"


def wire_key(wire: Wire) -> str:
    """
    The name of a wire in the circuit file: the input port ("Led.I"), with the output
    port if the input has more than one driver ("Led.I<T0.Y")
    """
    src_port, dst_port = wire
    if len(dst_port.get_drivers()) > 1:
        return f"{port_key(dst_port)}<{port_key(src_port)}"
    return port_key(dst_port)


def is_connection(wire: Wire) -> bool:
    """Is a wire a connection of the circuit: from an output port that drives the input port"""
    src_port, dst_port = wire
    return src_port.is_output() and dst_port in src_port.wired_ports


def drawn_key(wire: Wire) -> str:
    """
    The name of a drawn wire in the circuit file: of its connection (see wire_key), or
    "end<start" for a wire that is no connection, between ports of the same kind
    """
    if is_connection(wire):
        return wire_key(wire)
    return f"{port_key(wire[1])}<{port_key(wire[0])}"
