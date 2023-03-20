# DigSim - Interactive Digital Logic Simulator

<p align="center">
  <img alt="The DigSim Application" src="docs/images/screenshot_digsim_app.png" width=85%>
</p>

[DigSim Docs](docs/documentation.md)

## Quickstart

### Install
```
> python -m pip install .[app]
```

### Start Interactive GUI

```
> python -m digsim.app
```

### Start with example circuit
```
> python -m digsim.app --load example_circuits/yosys_counter.circuit
```

### Run examples
```
> python examples/example_sr.py
```

### Look at waveforms
```
> python examples/example_sr.py
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

[SOURCES](verilog/SOURCES.md)

## Development ToDo List

### Documentation
   * Add documentation :-)
### Model
   * Add unittest of all components
   * Add unittest of ports
