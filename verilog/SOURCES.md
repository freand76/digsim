# Verilog Sources

Some verilog files have been "borrowed" from different github repositories,
I will try to keep track of them and give credits!

## ICs written from their datasheets

These ICs are written for DigSim from the descriptions in their datasheets, and tested
against models of the datasheets in `tests/test_ics.py`: 74181, 74182, 74283, 7485,
74138, 74139, 74148, 74151, 74157, 74161, 74162, 74163, 74164, 74165, 74173, 74193,
74194, 74245, 74374, 74574, 74595 (`verilog/74xx`), 4017, 4021, 4029, 4094 and 4511
(`verilog/4000`).
`verilog/synth.sh` synthesizes them into the netlists in
`src/digsim/circuit/components/ic`.

## 6502 CPU [Link](https://github.com/Arlet/verilog-6502)
```
> python3 -m digsim.synth synth -i verilog/6502/ALU.v verilog/6502/cpu.v -o examples/yosys_6502/6502_primitives.json -t cpu
> python3 -m digsim.synth synth -i verilog/6502/ALU.v verilog/6502/cpu.v -o examples/yosys_6502/6502_functional.json -t cpu --functional
```
