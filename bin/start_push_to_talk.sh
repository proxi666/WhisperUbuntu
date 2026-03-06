#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$ROOT_DIR/.venv/bin/activate"
exec python "$ROOT_DIR/scripts/push_to_talk_listener.py" --key f8 --output-mode both
