# Break for error
set -e

echo "Executing pytest"
uv venv .test_venv
source .test_venv/bin/activate
uv pip install . pytest --python .test_venv/bin/python
uv run --active pytest $@
