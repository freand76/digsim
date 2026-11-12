# Build the wheels and sdists of the release in dist/: digsim-logic-simulator (the GUI)
# and digsim-engine (engine/), each from its sdist. Upload them with: twine upload dist/*
set -e

# Delete old dists
rm -rfv dist/*

echo "Build dist"
uv build --all-packages --out-dir dist

# The pinned requirements of the app, digsim-engine from dist/ (it isn't on PyPI before
# the release)
echo "Compile requirements.txt"
uv pip compile pyproject.toml --no-sources --find-links dist --output-file requirements.txt

# Print dist files
echo "Dist files:"
ls -l dist/*
