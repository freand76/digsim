# Verilog and Yosys

DigSim simulates Verilog designs by first turning them into a
[netlist](https://en.wikipedia.org/wiki/Netlist), a list of gates and how they are
connected. This is done with [Yosys](https://github.com/YosysHQ/yosys), an open-source
Verilog synthesis tool.

DigSim ships with [YoWASP](https://github.com/YoWASP/yosys), a portable WebAssembly build
of Yosys, so nothing extra needs to be installed. DigSim always uses it, also when
another `yosys` is installed.

!!! warning "Folders that Yosys can't read"
    YoWASP runs Yosys in a WebAssembly sandbox, which doesn't see every file:

    - `/tmp` on Linux and `/share`: YoWASP has folders of its own with these names,
      which hide the real ones. On macOS `/tmp` works, DigSim uses its real path
      `/private/tmp`.
    - Files directly in `/`.
    - Network paths on Windows (`\\server\share\...`). A network folder with a drive
      letter works.

    Synthesis fails with a message that says so, and `yosys_path_problem()` in
    `digsim.synth` tells beforehand. A path through a link works: DigSim gives Yosys the
    real path, as the sandbox doesn't follow links to absolute paths. Files that the
    Verilog includes with `` `include `` are read by Yosys itself, keep them in the same
    places.

You don't always need to synthesize by hand: the GUI and `YosysComponent` both accept
`.v` files and synthesize them on load. Creating a netlist yourself is useful when the
design has several modules, or when the same design is loaded often (synthesis of large
designs takes a while).

## The synthesis helper

DigSim includes a small command-line helper:

```sh
python -m digsim.synth synth -i <file1.v> [<file2.v> ...] -o <netlist.json> -t <top_module>
```

| Option | Description |
| --- | --- |
| `-i`, `--input-files` | One or more Verilog files |
| `-o`, `--output-file` | The JSON netlist to write |
| `-t`, `--top` | The name of the top module |
| `-s`, `--silent` | Hide the Yosys output |
| `-f`, `--functional` | Synthesize into functional blocks instead of gates, see below |
| `-p`, `--parameters` | Values for parameters of the top module, like `-p WIDTH=16 DEPTH=4`, see below |

To list the modules found in a set of Verilog files, with their parameters and the
defaults, as `-p` takes them:

```sh
python -m digsim.synth list -i <file1.v> [<file2.v> ...]
```

## Synthesis from Python

```python
from digsim.synth import Synthesis

synthesis = Synthesis(["counter.v"], "counter")
synthesis.synth_to_json_file("counter.json")
```

`synth_to_dict()` returns the netlist instead of writing it, see
[Verilog Testbench with pytest](testbenches.md).

## Parameters

The parameters of the top module keep their defaults, unless the synthesis gives them
other values. The values are integers, also negative ones and ones wider than 32 bits.

```python
synthesis = Synthesis(["fifo.v"], "fifo", parameters={"WIDTH": 16, "DEPTH": 4})
fifo = YosysComponent(circuit, path="fifo.v", parameters={"WIDTH": 16, "DEPTH": 4})
```

A `YosysComponent` also takes them as text, `parameters="WIDTH=16,DEPTH=4"`, and a saved
circuit keeps them. Each set of parameters is a netlist of its own, so two components of
the same file can have different ports. A parameter that the module doesn't have is a
synthesis error. A netlist file has no parameters, they were set when it was
synthesized. `Synthesis.list_parameters("fifo.v", "fifo")` returns the parameters of a
module and their defaults, and `Synthesis.list_module_parameters()` those of every module
in the files.

In the GUI, **Build > Parameters...** in the [Verilog editor](verilog-tutorial.md) shows
the parameters of the module, with their defaults, and a column for each component of
the file. An empty value is the default. **Synthesize** saves the file and synthesizes
each component with its values, and asks first if that changes the ports of a component,
like a wider bus does. Undo brings the values from before back, unless the ports changed.

## Gates or functional blocks

By default, Yosys synthesizes a design into gates and one-bit flip-flops, like `AND`, `OR`
and `DFF`. With `functional=True` (or `--functional` on the command line), it stops
before that and keeps functional blocks: adders, comparisons, multiplexers and registers
as wide as in the Verilog.

```python
synthesis = Synthesis(["counter.v"], "counter", functional=True)
```

A netlist with functional blocks has far fewer cells, so it simulates faster. Between
functional blocks, the bits of a port are also sent as one word instead of one bit at a
time. The 6502 CPU in the [examples](examples.md#6502-cpu) has 2047 cells as gates and 431
as functional blocks, and runs about 1.6 times faster. The simulation is the same for the
ports of the design. Inside it there are no gates, and the signals between the functional
blocks are not in a VCD file, only the ports of the design and the blocks' ports to them.

`YosysComponent(circuit, path="counter.v", functional=True)` synthesizes a Verilog file
into functional blocks, and in the GUI a checkbox after the file selects it. A netlist
file is used the way it was synthesized.

A netlist made with another Yosys flow can be loaded too. DigSim simulates all the
functional cells of Yosys that can be simulated, also the ones that the functional
synthesis doesn't make: the adders and multipliers of `alumacc` (`$alu`, `$macc_v2`,
`$lcu`, `$fa`) and lookup tables (`$lut`, `$sop`). Memories (`$mem_v2`) and extracted state machines (`$fsm`) are not simulated.
Synthesize with `memory_map`, and without the FSM passes (`synth -nofsm`) or with
`fsm_map`, like the functional synthesis does.

## Tristate outputs

An output that is not always driven, like `assign y = oe ? a : 'bz;`, is a tristate output
of the component: it is `"Z"` (high impedance) when it doesn't drive, so other outputs on
the same wire decide its value, see [Python Circuits](python.md#components-and-ports).
Inside a design, several tristate drivers on one bus are merged into one, and tristate
buses that don't reach an output port become ordinary logic (the Yosys pass
`tribuf -merge -logic`). DigSim components have no bidirectional (`inout`) ports.

## Internal signals and states

A Yosys netlist also has the names of the wires and registers of the Verilog, with the
bits they use. With `signals=True`, a `YosysComponent` makes them readable, and writes
them to the VCD file next to the ports. It makes the simulation slower, so it is off by
default.

```python
cpu = YosysComponent(circuit, path="cpu.json", signals=True, states=["state"])
cpu.signal_names()  # ["ABH", "ABL", ..., "PC", "state", ...]
cpu.signal("PC")  # The value, like a port value: a number or "X"
cpu.state("state")  # The name of the state, like "FETCH"
```

The names are hierarchical after flattening, like `ALU.OUT` for the signal `OUT` in the
submodule `ALU`.

A signal with names for its values, like the state of a state machine, is written to the
VCD file twice: as its value, like the other signals, and as text, the name of its
value, in a variable with `_name` after the signal's name (`state_name` for `state`).
A viewer like GTKWave shows both. The names come from:

- **A SystemVerilog enum**: Yosys keeps the names of an enum in the netlist, so a state
  declared as an enum always has them. This is the reliable way.
- **Parameters**: the module parameters with the width of the signal, a common way to
  name states in Verilog (`parameter FETCH = 6'd8`). A value with more names gets them
  all, separated by "/". Every signal with at least two names this way gets them, also
  one that isn't a state but has the same width as the states.

Signals of one bit, and signals with only one name, get no names, unless they are listed
in `states`. The functional synthesis keeps the encoding of a state machine, so that the
names fit. Gate-level and functional netlists have the same named signals. In the GUI,
the settings of a Yosys component have a checkbox for the signals, and the names come
with them.

A change of a signal with several bits can be written as two changes at the same time in
the VCD file, while its bits change one at a time, like the ports of a Yosys component.
A viewer shows the last one.

## Running Yosys directly

Yosys is also available as the `yowasp-yosys` command. Start it interactively:

```sh
yowasp-yosys
```

The following script is what DigSim itself uses, and gives good results:

```text
read -sv <verilog_file.v>
hierarchy -top <top_module>
proc; flatten
memory_dff
proc; opt; techmap; opt
synth -noabc -top <top_module>
write_json <netlist.json>
```

Save the commands in a file to run them as a script:

```sh
yowasp-yosys <script.ys>
```

## Formatting Verilog

DigSim can format Verilog and SystemVerilog files. Only the whitespace changes: each line
gets its indentation from the blocks (`module`, `begin`, `case` and so on) and the
brackets it is in, and a line that doesn't end its statement, like `if (a)`, indents the
next line. Whitespace at the end of lines goes, and there is at most one empty line in a
row. Comments and strings stay as they are.

```sh
python -m digsim.verilog format <file.v>              # print the formatted file
python -m digsim.verilog format -i <file.v> [...]     # format the files
python -m digsim.verilog format --check <file.v> [...]
```

| Option | Description |
| --- | --- |
| `-i`, `--in-place` | Write the formatted files back |
| `--check` | List the files that would change, with exit code 1 |
| `--indent` | Spaces for each step of indentation (default 4) |
| `--blank-lines` | The most empty lines in a row (default 1) |

The formatter checks that the formatted code has the same tokens as before. If it would
not, the file is left as it is, and the exit code is 2. From Python:

```python
from digsim.verilog import VerilogFormatter

with open("counter.v", encoding="utf-8") as file:
    formatted = VerilogFormatter(indent=4).format(file.read())
```

## Limitations

- A Verilog file loaded directly into a Yosys component can contain only one module.
  Synthesize multi-module designs into a netlist first.

See the [Yosys documentation](https://yosyshq.readthedocs.io/projects/yosys/) for
everything else Yosys can do.
