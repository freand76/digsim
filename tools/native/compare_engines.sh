#!/bin/sh
# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

# Run the 6502 example and the rewire test with the Python and the native engine, and
# check that their output and VCD files are byte-identical. Prints the run times.
set -e
cd "$(dirname "$0")/../.."
OUT=$(mktemp -d)
for args in "" "--functional" "--signals" "--functional --signals"; do
    for engine in python native; do
        # shellcheck disable=SC2086
        DIGSIM_ENGINE=$engine .venv/bin/python examples/yosys_6502/example_yosys_6502.py \
            $args --vcd "$OUT/$engine.vcd" > "$OUT/$engine.txt"
        grep "^Simulated" "$OUT/$engine.txt" | sed "s/^/$engine $args: /"
        sed -i '/^Simulated/d' "$OUT/$engine.txt"  # The run time always differs
    done
    cmp "$OUT/python.vcd" "$OUT/native.vcd"
    cmp "$OUT/python.txt" "$OUT/native.txt"
done
for engine in python native; do
    DIGSIM_ENGINE=$engine .venv/bin/python tools/native/rewire_6502.py "$OUT/$engine.vcd" > /dev/null
done
cmp "$OUT/python.vcd" "$OUT/native.vcd"
rm -rf "$OUT"
echo "The engines agree"
