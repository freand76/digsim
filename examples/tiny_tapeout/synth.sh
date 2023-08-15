#!/bin/env bash

SCRIPT_DIR=$(dirname $0)

python3 -m digsim.synth synth -i $SCRIPT_DIR/demodesign.v -o $SCRIPT_DIR/tinytapeout.json --top demodesign
