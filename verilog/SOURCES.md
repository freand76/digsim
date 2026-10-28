# Verilog Sources

Some verilog files have been "borrowed" from different github repositories,
I will try to keep track of them and give credits!

## ICs written from their datasheets

These ICs are written for DigSim from the descriptions in their datasheets, and tested
against models of the datasheets in `tests/test_ics.py`: 74181, 74182, 74283, 7485,
74138, 74151, 74162, 74164, 74165, 74193, 74194, 74595 (`verilog/74xx`), 4017 and 4511
(`verilog/4000`).
`verilog/synth.sh` synthesizes them into the netlists in
`src/digsim/circuit/components/ic`.

## 6502 CPU [Link](https://github.com/Arlet/verilog-6502)
```
> python3 -m digsim.synth synth -i verilog/6502/ALU.v verilog/6502/cpu.v -o examples/yosys_6502/6502_primitives.json -t cpu
> python3 -m digsim.synth synth -i verilog/6502/ALU.v verilog/6502/cpu.v -o examples/yosys_6502/6502_functional.json -t cpu --functional
```
