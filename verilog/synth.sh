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
