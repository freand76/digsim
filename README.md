# DigSim - Interactive Digital Logic Simulator

![Python Version from PEP 621 TOML](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2Ffreand76%2Fdigsim%2Fmain%2Fpyproject.toml)
![PyPI - Version](https://img.shields.io/pypi/v/digsim-logic-simulator)
![PyPI - Downloads](https://img.shields.io/pypi/dm/digsim-logic-simulator)
[![Documentation](https://img.shields.io/badge/docs-freand76.github.io%2Fdigsim-blue)](https://freand76.github.io/digsim/)

<p align="center">
  <img alt="The DigSim Application" src="https://raw.githubusercontent.com/freand76/digsim/af1bf95eb16d1af19f26159a4c1e1b88565703d7/docs/images/screenshot_digsim_app.png" width=85%>
</p>

DigSim is an interactive digital logic simulator written in Python. It is made for
learning and experimenting with digital logic, from single gates to complete Verilog
designs: build a circuit on the canvas, start the simulation, and press buttons, flip
switches and watch LEDs and hex displays react in real time.

Simulating Verilog normally means writing test stimuli and reading waveforms afterwards.
Testing on an FPGA is interactive, but every change means a slow synthesis and
programming cycle. DigSim sits in between: load a Verilog module, wire it to buttons and
displays, and play with it right away. It is even fast enough to run a synthesized
[6502 CPU](https://en.wikipedia.org/wiki/MOS_Technology_6502).

**📖 Documentation: <https://freand76.github.io/digsim/>**

## Features

- **Interactive GUI**: build and simulate circuits with buttons, switches, clocks, LEDs,
  hex digits, 7-segment displays, a buzzer and a logic analyzer.
- **Python API**: create and simulate circuits in Python, for scripts or pytest
  testbenches.
- **Verilog support**: turn Verilog into components with a bundled WebAssembly build of
  [Yosys](https://github.com/YosysHQ/yosys). Nothing extra to install.
- **Waveforms**: save simulation results as VCD files and view them in
  [GTKWave](https://gtkwave.sourceforge.net/).

## Installation and running

DigSim requires Python 3.10 or newer and is published on PyPI as
[`digsim-logic-simulator`](https://pypi.org/project/digsim-logic-simulator/). Choose the
option that fits what you want to do. See the
[installation guide](https://freand76.github.io/digsim/installation/) for more details.

### Option 1: Run without installing (uvx)

With [uv](https://docs.astral.sh/uv/) installed, this downloads and starts DigSim in a
temporary environment:

```sh
uvx digsim-logic-simulator
```

### Option 2: Install as an application

Installs DigSim in its own isolated environment and adds the `digsim-logic-simulator`
command to your `PATH`:

```sh
uv tool install digsim-logic-simulator    # or: pipx install digsim-logic-simulator
digsim-logic-simulator
```

### Option 3: Install as a Python package

Use this to `import digsim` in your own scripts and tests. Install it into a virtual
environment:

```sh
python3 -m venv .venv
source .venv/bin/activate                 # Windows: .venv\Scripts\activate
pip install digsim-logic-simulator
python -m digsim.app                      # start the GUI
```

### Option 4: Run from source

Clone the repository to get the example circuits and Python examples, or to work on
DigSim itself:

```sh
git clone https://github.com/freand76/digsim.git
cd digsim
uv sync                                   # or: pip install -e . (in a virtual environment)
uv run -m digsim.app
```

### Command-line options

```sh
digsim-logic-simulator --load example_circuits/counter_yosys_netlist.circuit   # open a circuit
digsim-logic-simulator --version                                               # show version
```

### Linux: Qt "xcb" plugin error

If startup fails with *Could not load the Qt platform plugin "xcb"*, install the missing
library (Ubuntu/Debian):

```sh
sudo apt install libxcb-cursor0
```

If that doesn't help, see
[troubleshooting](https://freand76.github.io/digsim/installation/#troubleshooting) for how
to find other missing libraries.

## Using DigSim

The commands below are run from the repository root (Option 4).

**Simulate a circuit in Python and view the waveforms:**

```sh
uv run python examples/example_sr.py
gtkwave sr.vcd
```

**Test a Verilog design with pytest:**

```sh
uv run --with pytest pytest examples/pytest_tb
```

**Synthesize Verilog into a netlist for DigSim:**

```sh
uv run -m digsim.synth synth -i <file1.v> [<file2.v> ...] -o <netlist.json> -t <top_module>
```

Read more in the documentation:

- [GUI Application](https://freand76.github.io/digsim/gui/): the circuit editor,
  components, simulation and shortcuts
- [Python Circuits](https://freand76.github.io/digsim/python/): the Python API and
  testbenches
- [Verilog and Yosys](https://freand76.github.io/digsim/synthesis/): synthesizing your own
  designs
- [Examples](https://freand76.github.io/digsim/examples/): every example with circuit
  diagrams, expected output and waveforms

## Development

```sh
uv tool run ruff format && uv tool run ruff check   # format and lint
uv run --with pytest pytest                         # run the tests
uv run --with mypy --with types-pexpect mypy        # type check
uv tool run --with mkdocs-material mkdocs serve     # preview the documentation
```

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=freand76/digsim&type=Date)](https://star-history.com/#freand76/digsim&Date)
