echo "Starting DigSim application"
uv venv .pypi_venv
uv pip install digsim-logic-simulator --upgrade
uv run -m digsim.app $@
