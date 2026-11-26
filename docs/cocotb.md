# Verilog Testbench with cocotb

DigSim can be the simulator for [cocotb](https://www.cocotb.org/) testbenches. Yosys
synthesizes the Verilog design into a netlist, and DigSim simulates it in the Python
process of the tests, so there is no simulator to install and no build step to compile
the design. cocotb's tests run as they do with other simulators: `await RisingEdge(dut.clk)`,
`dut.count.value`, clocks, triggers and the results file.

!!! note "A proof of concept"
    DigSim as a cocotb simulator is experimental. `python -m digsim.cocotb` works with
    cocotb 2.1, the release on PyPI. `make SIM=digsim`, the `DigSim` runner of
    `cocotb_tools.runner` and `--cocotb-simulator=digsim` of cocotb's pytest plugin need a
    cocotb with DigSim support, which is not released yet.

Install DigSim and cocotb into a virtual environment, see
[Installation](installation.md#install-into-a-virtual-environment):

```sh
pip install digsim-engine cocotb
```

## Running the tests

A cocotb test module, like `counter_tests.py` of cocotb's
[first steps](https://docs.cocotb.org/en/stable/first_steps.html), runs on a Verilog
design with:

```sh
python -m digsim.cocotb counter.sv --toplevel counter --test-modules counter_tests
```

The test modules are found in the current folder. `digsim-cocotb` is the same command.
`--toplevel` and `--test-modules` default to the environment variables `COCOTB_TOPLEVEL`
and `COCOTB_TEST_MODULES`, and the other `COCOTB_` variables, like `COCOTB_TEST_FILTER`
and `COCOTB_RESULTS_FILE`, work as with other simulators. Arguments that start with `+`
are plusargs for the tests (`cocotb.plusargs`).

| Option | |
| --- | --- |
| `--toplevel NAME` | The top module, needed with several files or with `-I` and `-D` (one file: its top module) |
| `--test-modules NAMES` | The Python modules with the tests, separated by commas |
| `-I FOLDER` | A folder to include files from, after the folder of the including file |
| `-D NAME[=VALUE]` | A macro, like `` `define ``, also a string: `'-DFILE="data/rom.hex"'` |
| `-P NAME=VALUE` | A value for a parameter of the top module, an integer like `8`, `0x10` or `8'd5` |
| `--functional` | Synthesize into functional blocks instead of gates, which simulates faster |
| `--waves FILE` | Write the waveforms to a VCD file |
| `--no-signals` | Leave out the named signals inside the design, and the logic that only they use, for a faster simulation |
| `--netlist FILE` | Only synthesize: write the netlist to a `.json` file, then give the file instead of the Verilog files to run the tests on it |

## With cocotb's Makefiles, runner and pytest plugin

With a cocotb that has DigSim support, DigSim is chosen like the other simulators:

```sh
make SIM=digsim
make SIM=digsim WAVES=1  # sim_build/<toplevel>.vcd
```

`VERILOG_INCLUDE_DIRS` gives include folders, and `COMPILE_ARGS` can give macros and
parameters as `-DNAME=VALUE` and `-PNAME=VALUE`. `SIM_ARGS=--no-signals` leaves out the
signals inside the design. With the runner, `build_args=["--no-signals"]` leaves them out
of the netlist, and `test_args=["--no-signals"]` out of the simulation.

The Python runner synthesizes the design in `build()`, to `sim_build/<toplevel>.json`,
and `test()` runs the tests on that netlist (it synthesizes again for other parameters):

```python
from cocotb_tools.runner import get_runner

runner = get_runner("digsim")
runner.build(sources=["counter.sv"], hdl_toplevel="counter")
runner.test(test_module="counter_tests", hdl_toplevel="counter", waves=True)
```

cocotb's pytest plugin selects DigSim with `--cocotb-simulator=digsim`, or finds it with
`auto` (the `digsim-cocotb` command) when no other simulator is installed.

## What the tests see

- The ports of the top module, and the named signals inside it, the wires and registers:
  `dut.value` for a register of the top module, `dut.u_sub.signal` for one of the
  submodule `u_sub`. Triggers like `RisingEdge` work on all of them. They are kept with
  the logic that drives them, also when no output depends on them, see `keep_signals` in
  [Synthesis](synthesis.md#internal-signals-and-states). A submodule without signals of
  its own is not seen, nor a generate block.
- A vector is a packed object (`PackedArrayObject`, `PackedObject` in cocotb 2.1), with
  the range and the signedness of its declaration: `dut.down[11]` is the bit of index 11
  of `logic [11:4] down`. A signal with a constant value, like a register that only an
  `initial` block sets, is read only.
- Only the inputs of the top module can be set, with deposits. A write to another signal
  is logged as an error of the `gpi` logger and ignored, like a write that a simulator
  rejects.
- A value is defined, or undefined (`X`) or not driven (`Z`) as a whole: a write of
  `0b01X0` sets `X`. The bits of an input can be set one at a time (`dut.din[0]`), a
  vector with an undefined bit reads as `X`.
- An `enum` declared without a type (an `int`, signed) reads as unsigned: Yosys doesn't
  mark it signed.
- One time step is a picosecond, and every gate has a delay of one step, so that the
  gates of the netlist settle long before the next edge of a clock of the tests. A test
  that reads an output in the time step of a clock edge sees its old value, as with
  registers in other simulators. `await Timer(1, "ns")` after the edge gives the new one.
- The VCD file (`--waves`) is in picoseconds, with the ports, the gates and the named
  signals.

Only the synthesizable subset of Verilog and SystemVerilog works: no `initial` blocks
with delays, no `$display`, no VHDL. SystemVerilog `timeunit` and `timeprecision` are
ignored, DigSim has a time of its own.
