#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"
ROOT_DIR="$SCRIPT_DIR"
source "$ROOT_DIR/.venv/bin/activate"
exec python "$ROOT_DIR/scripts/voice_hotkey_daemon.py" --model large-v3-turbo --compute-type float16
