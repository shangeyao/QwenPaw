#!/usr/bin/env bash
# Build and upload calb-qwenpaw to PyPI (shangeyao account).
# Fork repo: https://github.com/shangeyao/QwenPaw
# Usage: PYPI_API_TOKEN=pypi-xxx bash scripts/publish_pypi.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

bash "$REPO_ROOT/scripts/wheel_build.sh"

python3 -m pip install --quiet --upgrade twine
python3 -m twine upload dist/* "$@"

echo "[publish_pypi] Uploaded to https://pypi.org/project/calb-qwenpaw/"
