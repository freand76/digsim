# Break for error
set -e

echo "Executing pytest"
uv venv .test_venv
uv pip install . pytest
uv run pytest $@
