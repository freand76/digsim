# DigSim - Interactive Digital Logic Simulator

## Install
```
> python -m pip install .[app]
```

## Start Interactive GUI

### Start
```
> python -m digsim.app
```

### Start with example circuit
```
> python -m digsim.app --load example_circuits/yosys_counter.circuit
```

## Examples

### Run
```
> python examples/example_sr.py
```
### Look at waveforms
```
> gtkwave sr.vcd
```

## Yosys synthesis helper tool

**Yosys** must be installed and in your path
```
> python -m digsim.synth -i <verilog file 1> <optional verilog file 2> -o <output_file.json> -t <verilog top_module> 
```

## External verilog files and how to synthesise them

Some verilog files have been "borrowed" from different github repositories,
I will try to keep track of them and give credits!

[SOURCES](https://github.com/freand76/digsim/blob/main/verilog/SOURCES.md)

## Development ToDo List
 
### Documentation
   * Add documentation :-)
### Yosys
   * Add unittest of yosys atoms
### Model
   * Add unittest of all components
   * Add unittest of ports
