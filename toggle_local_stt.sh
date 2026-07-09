#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"

if (($#)); then
  exec "$SCRIPT_DIR/whisperubuntu.sh" "$@"
else
  exec "$SCRIPT_DIR/whisperubuntu.sh" toggle
fi
