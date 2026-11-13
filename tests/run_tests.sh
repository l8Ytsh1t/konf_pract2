#!/bin/sh
set -eu
PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PYTHON=python3
if [ -x "$PROJECT_DIR/.venv/bin/python" ]; then
    PYTHON="$PROJECT_DIR/.venv/bin/python"
fi
exec "$PYTHON" -m unittest discover -s "$PROJECT_DIR/tests" -p 'test_*.py' "$@"
