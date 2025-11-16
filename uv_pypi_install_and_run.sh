echo "Starting DigSim application"
uv venv .pypi_venv
source .pypi_venv/bin/activate
uv pip install digsim-logic-simulator --upgrade --python .pypi_venv/bin/python
uv run --active -m digsim.app $@
