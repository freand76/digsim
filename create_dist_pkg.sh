# Break for error
set -e

# Delete old dists
rm -rfv dist/*

# Install needed packages
echo "Install tools"
pip3 install pip --upgrade > build.log
pip3 install pip-tools build twine >> build.log

# Build dist
echo "Build dist"
echo " - Compile"
pip-compile pyproject.toml 2>> build.log
echo " - Build"
python3 -m build >> build.log

# Print dist files
echo "Dist files:"
ls -l dist/*
