#!/usr/bin/env bash
set -euo pipefail

# Always run from the repository folder so relative imports/files work.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

exec python3 SIOgui.py
