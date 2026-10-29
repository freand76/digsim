# DigSim

**DigSim is an interactive digital logic simulator written in Python.**

It is made for learning and experimenting with digital logic, from single gates to
complete Verilog designs. Build a circuit by dragging components onto a canvas, start
the simulation, and press buttons, flip switches and watch LEDs and hex displays react
in real time.

![The DigSim application](images/screenshot_digsim_app.png){ width="85%" }

## Why DigSim?

Simulating a Verilog or VHDL design normally means writing test stimuli and reading
waveforms afterwards, which is not a very interactive way of working. Testing the design
on an FPGA gives you real buttons and LEDs, but synthesis and programming take time
(and sometimes money), so every change has a long turnaround.

DigSim sits in between. You can load a Verilog module straight into the simulator, wire
it to buttons, switches and displays, and play with it immediately. Edit the Verilog,
reload the component, and try again.

DigSim started as a way to visualize simple Verilog modules. It has since been used to
simulate larger designs, such as the classic
[6502 CPU](https://en.wikipedia.org/wiki/MOS_Technology_6502). It is slower than
dedicated simulators, but fast enough to be useful.

## Features

- **Interactive GUI**: build and simulate circuits with buttons, switches, clocks, LEDs,
  LED bars, hex digits, 7-segment displays, a buzzer and a logic analyzer.
- **Python API**: create and simulate circuits in plain Python code, for scripts or
  pytest testbenches.
- **Verilog support**: turn Verilog into simulatable components using a bundled
  WebAssembly build of [Yosys](https://github.com/YosysHQ/yosys). No separate install
  needed.
- **Waveforms**: write simulation results to VCD files and inspect them in
  [GTKWave](https://gtkwave.sourceforge.net/) or a similar viewer.

## How does DigSim compare?

DigSim combines things that are usually separate tools: a circuit editor to play with,
a Verilog simulator, and a Python API for testbenches. This is how it compares with some
other open source tools for digital logic:

| | DigSim | [Logisim Evolution](https://github.com/logisim-evolution/logisim-evolution) | [Digital](https://github.com/hneemann/Digital) | [cocotb](https://www.cocotb.org/) | [DigitalJS](https://github.com/tilk/digitaljs) |
| --- | --- | --- | --- | --- | --- |
| Graphical circuit editor | ✅ | ✅ | ✅ | ❌ | ❌ shows circuits, no editor |
| Interactive simulation (buttons, LEDs, displays) | ✅ | ✅ | ✅ | ❌ | ✅ |
| Verilog designs in the simulation | ✅ | ❌ VHDL components | ✅ | ✅ | ✅ through Yosys |
| Verilog support included, no other tools to install | ✅ bundled Yosys | ❌ | ❌ needs Icarus Verilog | ❌ needs an HDL simulator | ✅ online version |
| Python API for circuits and testbenches | ✅ | ❌ Tcl console | ❌ | ✅ | ❌ JavaScript API |
| Automated tests | ✅ pytest | ✅ test vectors | ✅ test cases | ✅ Python coroutines | ❌ |
| Waveforms | ✅ VCD files | ✅ chronogram | ✅ measurement graph | ✅ from the simulator | ❌ |
| Internal signals and state names of Verilog designs | ✅ | ❌ | ❌ | ✅ | ❌ |
| Subcircuits in the editor | ✅ also from Python | ✅ | ✅ | ❌ | ❌ |
| Export to Verilog or VHDL, FPGA boards | ❌ | ✅ | ✅ | ❌ | ❌ |
| Runs on Linux, Windows and macOS | ✅ | ✅ | ✅ | ✅ | ✅ in a browser |
| Installed with | pip / uv | installer or JAR | JAR (Java) | pip, plus a simulator | browser or npm |
| Written in | Python | Java | Java | Python | JavaScript |
| License | BSD (Clear) | GPL-3.0 | GPL-3.0 | BSD | BSD-2-Clause |

In short:

- **Logisim Evolution and Digital** are made for drawing circuits, with export to
  Verilog or VHDL and to FPGA boards. DigSim is lighter, but simulates Verilog without
  other tools, and its circuits can be built and tested from Python.
- **cocotb** is the established way to test Verilog and VHDL in Python, with a real HDL
  simulator such as Icarus Verilog or Verilator. It is faster for large designs, but has
  no circuit editor and nothing interactive. DigSim's pytest testbenches need nothing
  but `pip install`.
- **DigitalJS** shows and simulates Yosys-synthesized Verilog in the browser. DigSim
  also lets you draw the circuit around the design, and run it from Python.

Other things in DigSim that can be useful:

- **Gate-level or functional simulation**: synthesize Verilog into gates, or into
  functional blocks (adders, multiplexers, registers) for a faster simulation, see
  [Verilog and Yosys](synthesis.md#gates-or-functional-blocks).
- **Internal signals and states**: the registers and state machines inside a Verilog
  design can be read from Python and are written to the VCD file, with the states by
  name, see [Internal signals and states](synthesis.md#internal-signals-and-states).
- **Wires to shape**: wires with corners, wire trees and joints, saved with the circuit.
- **Subcircuits**: a circuit file used as a component of another circuit, through its
  In, Out and InOut ports, in the GUI and from Python, see [Subcircuits](gui.md#subcircuits).
- **Ready-made ICs**: 74-series chips, synthesized from Verilog.
- **Your own components**: in Python, and in the GUI with an image, see
  [Creating Components](components.md).

The table describes the tools as far as their documentation goes. Corrections are
welcome as [issues](https://github.com/freand76/digsim/issues).

## Get started

1. [Install DigSim](installation.md), or run it directly with `uvx digsim-logic-simulator`.
2. Build [your first circuit](first-circuit.md) in the GUI, step by step.
3. Look up components and controls in the [GUI reference](gui.md).
4. Script circuits and testbenches with the [Python API](python.md).
5. Bring your own [Verilog designs](synthesis.md).
6. Try the [examples](examples.md).
7. [Create your own components](components.md), [add them to the GUI](gui-components.md)
   and [contribute](contributing.md) them.

DigSim is open source and developed on
[GitHub](https://github.com/freand76/digsim). Bug reports and ideas are welcome as
[issues](https://github.com/freand76/digsim/issues).
