#!/bin/sh
# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

# Build the digsim-native next to DigSim (../digsim-native, or $NATIVE), install it in
# .venv and test DigSim with it: the tests with both engines, and the engines compared.
# Run it before pushing digsim-native: its CI tests DigSim only on a release tag.
# uv sync (or uv run without --no-sync) installs the pinned digsim-native again.
# Usage: sh tools/native/test_local_native.sh [last fuzz seed, default 10]
set -e
cd "$(dirname "$0")/../.."
NATIVE=${NATIVE:-../digsim-native}
SEEDS=${1:-10}
WHEELS=$(mktemp -d)
(cd "$NATIVE" && uv tool run maturin build --release --out "$WHEELS")
uv pip install --python .venv/bin/python --reinstall "$WHEELS"/*.whl
rm -rf "$WHEELS"
export PYTHON=.venv/bin/python
"$PYTHON" -c "from digsim.circuit import _native; assert _native.mode() == 'native'"
"$PYTHON" -m pytest -q
DIGSIM_ENGINE=python "$PYTHON" -m pytest -q
sh tools/native/compare_engines.sh
sh tools/native/fuzz_engines.sh 1 "$SEEDS"
sh tools/native/fuzz_blocks.sh 1 "$SEEDS"
echo "DigSim works with $NATIVE"
