# DigSim - Interactive Digital Logic Simulator

![Python Version from PEP 621 TOML](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2Ffreand76%2Fdigsim%2Fmain%2Fpyproject.toml)
![PyPI - Version](https://img.shields.io/pypi/v/digsim-logic-simulator)
![PyPI - Downloads](https://img.shields.io/pypi/dm/digsim-logic-simulator)

<p align="center">
  <img alt="The DigSim Application" src="https://raw.githubusercontent.com/freand76/digsim/af1bf95eb16d1af19f26159a4c1e1b88565703d7/docs/images/screenshot_digsim_app.png" width=85%>
</p>

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

### Install from PyPi
```
pip3 install digsim-logic-simulator
```

### Install from GitHub
```
> git clone https://github.com/freand76/digsim.git
> cd digsim
> python3 -m pip install .
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

### Start with example circuit (example circuits are available in the github repository)
```
> python3 -m digsim.app --load example_circuits/counter_yosys_netlist.circuit
```

### Run example (examples are available in the github repository)
```
> python3 examples/example_sr.py
```

### Look at waveforms
```
> python3 examples/example_sr.py
> gtkwave sr.vcd
```

### Examples of writing pytest/python test benches for synthesized verilog code
```
> pytest examples/pytest_tb
```

## Yosys synthesis helper tool

```
> python3 -m digsim.synth synth -i <verilog file 1> <optional verilog file 2> -o <output_file.json> -t <verilog top_module>
```

## Documentation

[Documentation](https://github.com/freand76/digsim/blob/main/docs/documentation.md) on GitHub

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=freand76/digsim&type=Date)](https://star-history.com/#freand76/digsim&Date)
