#!/bin/sh
# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

# Run the random circuits of fuzz_gates.py and fuzz_functional.py with the Python and the
# native engine, and check that their output and VCD files are byte-identical. Runs
# .venv/bin/python, or $PYTHON. The native engine runs with DIGSIM_BLOCKS=0: every cell
# with its delay and events, like in Python (blocks have no delays, see fuzz_blocks.sh).
# Usage: sh tools/native/fuzz_engines.sh [first seed] [last seed]
set -e
export DIGSIM_BLOCKS=0
cd "$(dirname "$0")/../.."
OUT=$(mktemp -d)
for script in fuzz_gates.py fuzz_functional.py; do
    for seed in $(seq "${1:-1}" "${2:-50}"); do
        for engine in python native; do
            DIGSIM_ENGINE=$engine "${PYTHON:-.venv/bin/python}" "tools/native/$script" "$seed" \
                "$OUT/$engine.vcd" > "$OUT/$engine.txt"
        done
        if ! cmp -s "$OUT/python.txt" "$OUT/native.txt" || \
                ! cmp -s "$OUT/python.vcd" "$OUT/native.vcd"; then
            echo "$script seed $seed: the engines differ, see $OUT"
            exit 1
        fi
    done
done
rm -rf "$OUT"
echo "The engines agree"
