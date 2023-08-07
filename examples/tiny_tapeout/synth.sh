#!/bin/env bash

SCRIPT_DIR=$(dirname $0)

python3 -m digsim.synth -i $SCRIPT_DIR/demodesign.v -o $SCRIPT_DIR/tinetapeout.json --top demodesign
