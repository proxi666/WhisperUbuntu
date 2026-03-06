#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"
ROOT_DIR="$SCRIPT_DIR"
SOCKET_PATH="${XDG_RUNTIME_DIR:-/tmp}/local-stt.sock"

# The daemon service may be active before its unix socket is actually ready.
for _ in $(seq 1 20); do
  if [[ -S "$SOCKET_PATH" ]]; then
    break
  fi
  sleep 0.25
done

source "$ROOT_DIR/.venv/bin/activate"
exec python "$ROOT_DIR/scripts/push_to_talk_listener.py" --key f8 --output-mode both
