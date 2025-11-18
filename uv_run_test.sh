# Break for error
set -e

echo "Executing pytest"
uv venv --clear .test_venv --python 3.13
source .test_venv/bin/activate
uv pip install . pytest --python .test_venv/bin/python
uv run --active pytest $@
