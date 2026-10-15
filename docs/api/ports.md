# Ports

The ports of a component are attributes with the name of the port, like `gate.A` and
`gate.Y`. Connect an output to an input with `output.wire = input`, and read or set a value
with `port.value`, either 0 or 1 (or a number for a bus), or `"X"` when it is unknown.

All port classes have the methods of `Port`. The other classes are used to write
[your own components](../components.md): they decide how a port updates its component and
the ports it drives.

::: digsim.circuit.components.atoms.Port
    options:
      members:
        - name
        - parent
        - path
        - value
        - width
        - wire
        - wired_ports
        - is_input
        - is_output
        - has_driver
        - get_driver
        - disconnect
        - remove_wires
        - is_rising_edge
        - is_falling_edge
        - strval

::: digsim.circuit.components.atoms.PortIn
    options:
      members: false

::: digsim.circuit.components.atoms.PortWire
    options:
      members: false

::: digsim.circuit.components.atoms.PortOutDelta
    options:
      members:
        - update_parent
        - set_delay_ns

::: digsim.circuit.components.atoms.PortOutImmediate
    options:
      members: false

::: digsim.circuit.components.atoms.PortMultiBitWire
    options:
      members:
        - get_bit

## Exceptions

::: digsim.circuit.components.atoms.PortConnectionError
    options:
      heading_level: 3
      members: false
