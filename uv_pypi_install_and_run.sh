echo "Starting DigSim application"
uv venv --clear .pypi_venv --python 3.13
source .pypi_venv/bin/activate
uv pip install digsim-logic-simulator --upgrade --python .pypi_venv/bin/python
uv run --active -m digsim.app $@
