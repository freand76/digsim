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

## Development ToDo List
 
### Documentation
   * Add documentation :-)
### Yosys
   * Add the rest of the yosys atoms
   * Add unittest of yosys atoms
### GUI
   * Clear circuit button
   * "Are you sure?" dialog for load/clear
### Model
   * Add "generic" IC catalog with synthesized 74xx components
   * Add unittest of all components
   * Add unittest of ports
