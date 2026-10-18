# Verilog and Yosys

DigSim simulates Verilog designs by first turning them into a
[netlist](https://en.wikipedia.org/wiki/Netlist), a list of gates and how they are
connected. This is done with [Yosys](https://github.com/YosysHQ/yosys), an open-source
Verilog synthesis tool.

DigSim ships with [YoWASP](https://github.com/YoWASP/yosys), a portable WebAssembly build
of Yosys, so nothing extra needs to be installed. If a native `yosys` is found on your
`PATH`, it is used instead.

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

To list the modules found in a set of Verilog files:

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

## Gates or functional blocks

By default, Yosys synthesizes a design into gates and one-bit flip-flops, like `AND`, `OR`
and `DFF`. With `functional=True` (or `--functional` on the command line), it stops
before that and keeps functional blocks: adders, comparisons, multiplexers and registers
as wide as in the Verilog.

```python
synthesis = Synthesis(["counter.v"], "counter", functional=True)
```

A netlist with functional blocks has far fewer cells, so it simulates faster. The 6502
CPU in the [examples](examples.md#6502-cpu) has 2047 cells as gates and 608 as functional
blocks, and runs about 1.3 times faster. The simulation is the same for the ports of the
design, but there are no gates inside to look at in the waveforms.

`YosysComponent(circuit, path="counter.v", functional=True)` synthesizes a Verilog file
into functional blocks, and in the GUI a checkbox after the file selects it. A netlist
file is used the way it was synthesized.

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

## Limitations

- A Verilog file loaded directly into a Yosys component can contain only one module.
  Synthesize multi-module designs into a netlist first.
- When reloading a component, its ports must keep the same names and widths.

See the [Yosys documentation](https://yosyshq.readthedocs.io/projects/yosys/) for
everything else Yosys can do.
