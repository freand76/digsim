# Break for error
set -e

# Delete old dists
rm -rfv dist/*

# Install needed packages
echo "Install tools"
uv venv --clear .dist_venv --python 3.13
source .dist_venv/bin/activate
uv pip install pip-tools build twine --upgrade --python .dist_venv/bin/python

# Build dist
echo "Build dist"
echo " - Compile"
pip-compile pyproject.toml
echo " - Build"
uv run --active -m build

# Print dist files
echo "Dist files:"
ls -l dist/*
