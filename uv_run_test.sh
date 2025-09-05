# Break for error
set -e

echo "Executing pytest"
uv venv .test_venv
. .test_venv/bin/activate
uv pip install . pytest
uv run --active pytest $@
