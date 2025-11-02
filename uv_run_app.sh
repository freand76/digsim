echo "Starting DigSim application"
uv venv .run_venv
uv pip install . --upgrade
uv run -m digsim.app $@
