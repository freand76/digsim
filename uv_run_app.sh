echo "Starting DigSim application"
uv venv --clear .run_venv --python 3.13
source .run_venv/bin/activate
uv sync --active
uv run --active -m digsim.app $@
