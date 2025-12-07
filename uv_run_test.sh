# Break for error
set -e

echo "Executing pytest"
uv venv --clear .test_venv --python 3.14
source .test_venv/bin/activate
uv sync --active
uv pip install pytest
uv run --active pytest $@
