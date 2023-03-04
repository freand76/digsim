# Verilog Sources

## 74162 [Link](https://github.com/TimRudy/ice-chips-verilog)
```
> python3 -m digsim.synth -i verilog/74xx/74162.v -o src/digsim/circuit/components/ic/74162.json -t ttl_74162
```

## 6502 CPU [Link](https://github.com/Arlet/verilog-6502)
```
> python3 -m digsim.synth -i verilog/6502/ALU.v verilog/6502/cpu.v -o examples/yosys_6502/6502.json -t cpu
```
