echo "Starting DigSim application"
uv venv .run_venv
source .run_venv/bin/activate
uv pip install . --upgrade --python .run_venv/bin/python
uv run --active -m digsim.app $@
