#!/usr/bin/env bash
# Build a single-file, windowed stock-client executable with PyInstaller.
#
# Usage:
#   packaging/build.sh            # build into dist/
#   packaging/build.sh --clean    # wipe build/ and dist/ first
#
# Requirements: a virtualenv with requirements.txt installed, plus PyInstaller
# (pip install pyinstaller). Tested with PyInstaller >= 6.x and PySide6 >= 6.6.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [[ "${1:-}" == "--clean" ]]; then
    rm -rf build dist
fi

# PyInstaller is a build-time-only dependency; install it if missing.
if ! python -c "import PyInstaller" 2>/dev/null; then
    echo "PyInstaller not found, installing..."
    python -m pip install pyinstaller
fi

# --noconfirm: overwrite previous build/dist without prompting.
# The spec file resolves ../run.py relative to the spec's own directory.
pyinstaller packaging/stockclient.spec --noconfirm

echo
echo "Done. Executable: dist/stock-client"
echo "Run it: ./dist/stock-client --demo   (offline demo, no network needed)"
