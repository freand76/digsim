#!/bin/env bash

SCRIPT_DIR=$(dirname $0)

python3 -m digsim.synth synth -i $SCRIPT_DIR/counter.v -o $SCRIPT_DIR/counter.json --top counter
