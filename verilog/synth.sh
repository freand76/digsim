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
