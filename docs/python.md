# Python Circuits

Everything you can build in the GUI can also be built in Python. This is useful for
automated tests of a design, for generating waveforms, or for mixing a simulated circuit
with ordinary Python code.

Install DigSim into a virtual environment first, see
[Installation](installation.md#install-into-a-virtual-environment). The runnable
examples referenced on this page are in the
[`examples`](https://github.com/freand76/digsim/tree/main/examples) folder of the
repository. Run them from the repository root.

## A first circuit

This example connects two push buttons to an SR latch and an LED, and writes all signals
to `sr.vcd` ([`examples/example_sr.py`](https://github.com/freand76/digsim/blob/main/examples/example_sr.py)):

```python
from digsim.circuit import Circuit
from digsim.circuit.components import SR, Led, PushButton


def led_callback(comp):
    state = "ON" if comp.ports[0].value == 1 else "OFF"
    print(f"{comp.circuit.time_ns:9}: LED '{comp.name()}' is {state}")


circuit = Circuit(vcd="sr.vcd")

set_button = PushButton(circuit, "S-Button")
reset_button = PushButton(circuit, "R-Button")
latch = SR(circuit)
led = Led(circuit, "D1", callback=led_callback)

set_button.O.wire = latch.S
reset_button.O.wire = latch.R
latch.Q.wire = led.I

circuit.init()
circuit.run(ms=10)

set_button.push()
circuit.run(ms=10)
set_button.release()
circuit.run(ms=10)

circuit.vcd_close()
```

Run it and look at the result:

```sh
python examples/example_sr.py
gtkwave sr.vcd
```

## Concepts

### The circuit

`Circuit` holds all components and the simulation time.

| Method | Description |
| --- | --- |
| `Circuit(name=None, vcd=None)` | Create a circuit, optionally writing a VCD file |
| `init()` | Initialize the circuit, after adding and connecting components |
| `run(s=, ms=, us=, ns=)` | Run the simulation for a period of time |
| `run_until(s=, ms=, us=, ns=)` | Run the simulation until an absolute time |
| `process_single_event(stop_time_ns=None)` | Process only the next event, to step through a simulation. Returns two booleans: if an event was processed (not if there were none, or the next one is after `stop_time_ns`), and if it was on a port of a top-level component rather than inside one, like a Yosys component. |
| `time_ns` | The current simulation time in nanoseconds |
| `get_component(name)` | Look up a component by name |
| `vcd(filename)` / `vcd_close()` | Start or finish writing a VCD file |
| `to_json_file(filename)` | Save the circuit. File paths in it, like a Verilog file, are stored relative to the file. |
| `from_json_file(filename, folder=None)` | Load a circuit, also a circuit file saved by the GUI, with the connections of its wires. Relative file paths in it are read from the file's folder, or from `folder` if it is given. |

### Components and ports

Components live in `digsim.circuit.components`. Each component is created with the
circuit as its first argument and an optional name. Ports are attributes on the
component, for example `latch.S` or `led.I`.

Connect an output port to an input port by assigning to `.wire`:

```python
button.O.wire = gate.A
```

Read a port's current value with `.value`. Inputs that are not driven by another
component can be set directly, which is handy in testbenches:

```python
dut.clk.value = 1
circuit.run(ms=1)
print(dut.cnt.value)
```

Several outputs can drive the same input. It then has the value that they drive, and
`"X"` (undefined) if they drive different values or one of them drives `"X"`. A
tristate output, like the output of a `TristateBuffer` or a Verilog output that can be
`'bz`, is `"Z"` (high impedance) when it doesn't drive, and the other outputs decide:

```python
first.Y.wire = led.I
second.Y.wire = led.I  # Both are TristateBuffer outputs
button.O.wire = led.I  # Its value, unless an enabled buffer drives another one
```

Interactive components have methods for controlling them, such as `PushButton.push()`
and `.release()`. Output components such as `Led` accept a `callback` that is called
whenever their value changes.

The available components are:

| Category | Components |
| --- | --- |
| Inputs | `PushButton`, `OnOffSwitch`, `DipSwitch`, `Clock`, `StaticValue`, `VDD`, `GND` |
| Outputs | `Led`, `LedBar`, `HexDigit`, `SevenSegment`, `Buzzer`, `LogicAnalyzer` |
| Gates | `AND`, `OR`, `NOT`, `XOR`, `XNOR`, `NAND`, `NOR`, `MUX` |
| Flip-flops | `DFF`, `SR`, `FlipFlop`, `SRFF`, `ClockedSRFF`, `ClockedJKFF`, `ClockedTFF` |
| Buses | `Bus2Wires`, `Wires2Bus`, `TristateBuffer`, `LabelWireIn`, `LabelWireOut` |
| Complex | `IntegratedCircuit`, `YosysComponent`, `Mem64kByte`, `MemStdOut` |

## Verilog components

A `YosysComponent` can be created straight from a Verilog file or from a Yosys JSON
netlist. Its ports get the names of the Verilog module's ports
([`examples/yosys_counter`](https://github.com/freand76/digsim/tree/main/examples/yosys_counter)):

```python
from digsim.circuit import Circuit
from digsim.circuit.components import VDD, PushButton, YosysComponent

circuit = Circuit(vcd="counter.vcd")
counter = YosysComponent(circuit, path="examples/yosys_counter/counter.v")
clk = PushButton(circuit, "clk")
vdd = VDD(circuit)

clk.O.wire = counter.clk
vdd.wire = counter.up

circuit.init()
```

See [Verilog and Yosys](synthesis.md) for more about synthesis.

## Testbenches with pytest

Because circuits are plain Python, a Verilog design can be tested with
[pytest](https://pytest.org/): synthesize the design in a fixture, then drive its inputs
and assert on its outputs. See [Verilog Testbench with pytest](testbenches.md).

## More examples

See [Examples](examples.md) for a walkthrough of every example, with circuit diagrams,
expected output and waveforms.


| Example | Shows |
| --- | --- |
| [`example_sr.py`](https://github.com/freand76/digsim/blob/main/examples/example_sr.py) | Buttons, an SR latch, an LED callback and VCD output |
| [`example_clock.py`](https://github.com/freand76/digsim/blob/main/examples/example_clock.py) | Using a clock component |
| [`load_save`](https://github.com/freand76/digsim/tree/main/examples/load_save) | Saving and loading circuits as JSON |
| [`synthesis`](https://github.com/freand76/digsim/tree/main/examples/synthesis) | Running Yosys synthesis from Python |
| [`yosys_counter`](https://github.com/freand76/digsim/tree/main/examples/yosys_counter) | A Verilog counter, from a netlist or straight from Verilog |
| [`yosys_6502`](https://github.com/freand76/digsim/tree/main/examples/yosys_6502) | A synthesized 6502 CPU running a program from memory |
| [`yosys_fsm`](https://github.com/freand76/digsim/tree/main/examples/yosys_fsm) | A SystemVerilog state machine, with the names of its states in the VCD file |
| [`pytest_tb`](https://github.com/freand76/digsim/tree/main/examples/pytest_tb) | pytest testbenches for Verilog designs |
