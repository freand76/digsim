# Break for error
set -e

echo "Ruffing project..."
echo " * Ruff Format..."
uv tool run ruff format
echo " * Ruff Check..."
uv tool run ruff check
