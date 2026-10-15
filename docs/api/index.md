# API Reference

The reference for using DigSim from Python, generated from the code. For an introduction,
see [Python Circuits](../python.md).

| Module | Contents |
| --- | --- |
| [`digsim.circuit`](circuit.md) | `Circuit`, which holds the components and runs the simulation |
| [`digsim.circuit.components`](components.md) | The components, like `AND`, `Led` and `YosysComponent` |
| [`digsim.circuit.components.atoms`](base-classes.md) | The [base classes](base-classes.md) of all components, and the [ports](ports.md) |
| [`digsim.synth`](synthesis.md) | `Synthesis`, Verilog to netlist with Yosys |
| [`digsim.utils`](netlist.md) | The Yosys netlist classes |

Modules with names that start with `_` are internal. Import everything from the modules
above.

## Ports

A component's ports are attributes with the name of the port, like `gate.A` and
`gate.Y`. The ports of each component are listed under **Ports** in its description.
Connect an output to an input with `output.wire = input`, and read or set a value with
`port.value`. See [Ports](ports.md).
