echo "Starting DigSim application"
uv venv .pypi_venv
. .pypi_venv/bin/activate
uv pip install digsim-logic-simulator
uv run --active -m digsim.app $@
