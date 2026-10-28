#!/bin/env bash

SCRIPT_DIR=$(dirname $0)

python3 -m digsim.synth synth \
        -i $SCRIPT_DIR/74xx/74162.v \
        -o $SCRIPT_DIR/../src/digsim/circuit/components/ic/74162.json \
        -t ttl_74162

python3 -m digsim.synth synth \
        -i $SCRIPT_DIR/74xx/7448.v \
        -o $SCRIPT_DIR/../src/digsim/circuit/components/ic/7448.json \
        -t ic7448

# The ICs written from their datasheets, see verilog/SOURCES.md
python3 -m digsim.synth synth \
        -i $SCRIPT_DIR/74xx/74181.v \
        -o $SCRIPT_DIR/../src/digsim/circuit/components/ic/74181.json \
        -t ttl_74181

python3 -m digsim.synth synth \
        -i $SCRIPT_DIR/74xx/74182.v \
        -o $SCRIPT_DIR/../src/digsim/circuit/components/ic/74182.json \
        -t ttl_74182

python3 -m digsim.synth synth \
        -i $SCRIPT_DIR/74xx/74283.v \
        -o $SCRIPT_DIR/../src/digsim/circuit/components/ic/74283.json \
        -t ttl_74283

python3 -m digsim.synth synth \
        -i $SCRIPT_DIR/74xx/7485.v \
        -o $SCRIPT_DIR/../src/digsim/circuit/components/ic/7485.json \
        -t ttl_7485

python3 -m digsim.synth synth \
        -i $SCRIPT_DIR/74xx/74138.v \
        -o $SCRIPT_DIR/../src/digsim/circuit/components/ic/74138.json \
        -t ttl_74138

python3 -m digsim.synth synth \
        -i $SCRIPT_DIR/74xx/74151.v \
        -o $SCRIPT_DIR/../src/digsim/circuit/components/ic/74151.json \
        -t ttl_74151

python3 -m digsim.synth synth \
        -i $SCRIPT_DIR/74xx/74164.v \
        -o $SCRIPT_DIR/../src/digsim/circuit/components/ic/74164.json \
        -t ttl_74164

python3 -m digsim.synth synth \
        -i $SCRIPT_DIR/74xx/74165.v \
        -o $SCRIPT_DIR/../src/digsim/circuit/components/ic/74165.json \
        -t ttl_74165

python3 -m digsim.synth synth \
        -i $SCRIPT_DIR/74xx/74193.v \
        -o $SCRIPT_DIR/../src/digsim/circuit/components/ic/74193.json \
        -t ttl_74193

python3 -m digsim.synth synth \
        -i $SCRIPT_DIR/74xx/74194.v \
        -o $SCRIPT_DIR/../src/digsim/circuit/components/ic/74194.json \
        -t ttl_74194

python3 -m digsim.synth synth \
        -i $SCRIPT_DIR/74xx/74595.v \
        -o $SCRIPT_DIR/../src/digsim/circuit/components/ic/74595.json \
        -t ttl_74595

python3 -m digsim.synth synth \
        -i $SCRIPT_DIR/4000/4017.v \
        -o $SCRIPT_DIR/../src/digsim/circuit/components/ic/4017.json \
        -t cmos_4017

python3 -m digsim.synth synth \
        -i $SCRIPT_DIR/4000/4511.v \
        -o $SCRIPT_DIR/../src/digsim/circuit/components/ic/4511.json \
        -t cmos_4511

python3 -m digsim.synth synth \
        -i $SCRIPT_DIR/4000/4021.v \
        -o $SCRIPT_DIR/../src/digsim/circuit/components/ic/4021.json \
        -t cmos_4021

python3 -m digsim.synth synth \
        -i $SCRIPT_DIR/4000/4029.v \
        -o $SCRIPT_DIR/../src/digsim/circuit/components/ic/4029.json \
        -t cmos_4029

python3 -m digsim.synth synth \
        -i $SCRIPT_DIR/4000/4094.v \
        -o $SCRIPT_DIR/../src/digsim/circuit/components/ic/4094.json \
        -t cmos_4094

python3 -m digsim.synth synth \
        -i $SCRIPT_DIR/74xx/74139.v \
        -o $SCRIPT_DIR/../src/digsim/circuit/components/ic/74139.json \
        -t ttl_74139

python3 -m digsim.synth synth \
        -i $SCRIPT_DIR/74xx/74148.v \
        -o $SCRIPT_DIR/../src/digsim/circuit/components/ic/74148.json \
        -t ttl_74148

python3 -m digsim.synth synth \
        -i $SCRIPT_DIR/74xx/74157.v \
        -o $SCRIPT_DIR/../src/digsim/circuit/components/ic/74157.json \
        -t ttl_74157

python3 -m digsim.synth synth \
        -i $SCRIPT_DIR/74xx/74161.v \
        -o $SCRIPT_DIR/../src/digsim/circuit/components/ic/74161.json \
        -t ttl_74161

python3 -m digsim.synth synth \
        -i $SCRIPT_DIR/74xx/74163.v \
        -o $SCRIPT_DIR/../src/digsim/circuit/components/ic/74163.json \
        -t ttl_74163

python3 -m digsim.synth synth \
        -i $SCRIPT_DIR/74xx/74173.v \
        -o $SCRIPT_DIR/../src/digsim/circuit/components/ic/74173.json \
        -t ttl_74173

python3 -m digsim.synth synth \
        -i $SCRIPT_DIR/74xx/74245.v \
        -o $SCRIPT_DIR/../src/digsim/circuit/components/ic/74245.json \
        -t ttl_74245

python3 -m digsim.synth synth \
        -i $SCRIPT_DIR/74xx/74374.v \
        -o $SCRIPT_DIR/../src/digsim/circuit/components/ic/74374.json \
        -t ttl_74374

python3 -m digsim.synth synth \
        -i $SCRIPT_DIR/74xx/74574.v \
        -o $SCRIPT_DIR/../src/digsim/circuit/components/ic/74574.json \
        -t ttl_74574

# The 6502 synthesized into gates and into functional blocks, see examples/yosys_6502
python3 -m digsim.synth synth \
        -i $SCRIPT_DIR/6502/ALU.v $SCRIPT_DIR/6502/cpu.v \
        -o $SCRIPT_DIR/../examples/yosys_6502/6502_primitives.json \
        -t cpu

python3 -m digsim.synth synth \
        -i $SCRIPT_DIR/6502/ALU.v $SCRIPT_DIR/6502/cpu.v \
        -o $SCRIPT_DIR/../examples/yosys_6502/6502_functional.json \
        -t cpu \
        --functional
