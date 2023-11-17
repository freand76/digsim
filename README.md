# DigSim - Interactive Digital Logic Simulator

<p align="center">
  <img alt="The DigSim Application" src="docs/images/screenshot_digsim_app.png" width=85%>
</p>

* **Table of contents**
  * [Introduction](#introduction)
  * [Quickstart](#quickstart)
  * [Yosys Helper Tool](#yosys-synthesis-helper-tool)
  * [Documentation](docs/documentation.md)
  * [Borrowed verilog](verilog/SOURCES.md)

## Introduction

DigSim is a python based framework for digital circuit simulation.
The main purpose of the software is to, in an educational way, play around with digital logic (simple gates and verilog designs).

When working with block design in Verilog/VHDL the simulation tools are normally fed with test stimuli (a very non-interactive way of working...)
A block design can be synthesized and tested on an FPGA (where there are possibilities for interactivity if buttons and LED/Hex digits are available),
but that often has a great cost in time (and sometimes money) leading to long turnaround time.

I started developing DigSim to make it easy to implement and visualize the functionality of simple verlog modules.
During development I tried to synthesize larger verilog designs, such as the classic [6502 CPU](https://en.wikipedia.org/wiki/MOS_Technology_6502),
and even if it is slower than many other simulators it is not entirely useless.

### Features
 * Create and simulate a circuit using python code
 * Create and simulate a circuit **interactively** using the GUI
 * Create new components using synthesized verilog code
 * Save simulation results in VCD files, which can be opened in for example GTKWave.

## Quickstart

### Install
```
> git clone https://github.com/freand76/digsim.git
> cd digsim
> python3 -m pip install .[app]
```

### Start Interactive GUI

```
> python3 -m digsim.app
```

**Note: Ubuntu**

If your Ubuntu installation gives the folloing error message:

*qt.qpa.plugin: Could not load the Qt platform plugin "xcb" in "" even though it was found.*
*This application failed to start because no Qt platform plugin could be initialized. Reinstalling the application may fix this problem.*

*Available platform plugins are: vnc, wayland, wayland-egl, eglfs, offscreen, xcb, minimal, linuxfb, vkkhrdisplay, minimalegl.*

Then the following package must be installed:
```
> apt install libxcb-cursor0
```

### Start with example circuit
```
> python3 -m digsim.app --load example_circuits/counter_yosys_netlist.circuit
```

### Run example
```
> python3 examples/example_sr.py
```

### Look at waveforms
```
> python3 examples/example_sr.py
> gtkwave sr.vcd
```

## Yosys synthesis helper tool

**Yosys** must be installed and in your path
```
> python3 -m digsim.synth synth -i <verilog file 1> <optional verilog file 2> -o <output_file.json> -t <verilog top_module>
```

## Development ToDo List

### Model
   * Add unittest of all components
   * Add unittest of ports
