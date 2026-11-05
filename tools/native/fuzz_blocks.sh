#!/bin/sh
# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

# Run the random netlists of fuzz_blocks.py, of gates and of functional cells, the 6502
# example and the rewire test with the Python engine and with the native engine (which
# simulates the Yosys components as compiled blocks), and check that their settled
# outputs, and what the 6502 prints, are the same. Runs .venv/bin/python, or $PYTHON.
# Usage: sh tools/native/fuzz_blocks.sh [first seed] [last seed]
set -e
cd "$(dirname "$0")/../.."
OUT=$(mktemp -d)
for args in "" "--functional" "--signals" "--functional --signals"; do
    for engine in python native; do
        # shellcheck disable=SC2086
        DIGSIM_ENGINE=$engine "${PYTHON:-.venv/bin/python}" examples/yosys_6502/example_yosys_6502.py \
            $args | grep -v "^Simulated" > "$OUT/$engine.txt"
    done
    cmp "$OUT/python.txt" "$OUT/native.txt"
done
# The engine stops when the wires change: the state of the blocks goes back to Python
for engine in python native; do
    DIGSIM_ENGINE=$engine "${PYTHON:-.venv/bin/python}" tools/native/rewire_6502.py "$OUT/$engine.vcd" \
        > "$OUT/$engine.txt"
done
cmp "$OUT/python.txt" "$OUT/native.txt"
for mode in gates functional; do
    for seed in $(seq "${1:-1}" "${2:-50}"); do
        for engine in python native; do
            DIGSIM_ENGINE=$engine "${PYTHON:-.venv/bin/python}" tools/native/fuzz_blocks.py \
                "$mode" "$seed" > "$OUT/$engine.txt"
        done
        if ! cmp -s "$OUT/python.txt" "$OUT/native.txt"; then
            echo "fuzz_blocks.py $mode seed $seed: the engines differ, see $OUT"
            exit 1
        fi
    done
done
rm -rf "$OUT"
echo "The engines agree"
