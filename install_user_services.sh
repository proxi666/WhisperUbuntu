#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
USER_SYSTEMD_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
USER_BIN_DIR="$HOME/.local/bin"

mkdir -p "$USER_SYSTEMD_DIR" "$USER_BIN_DIR"

chmod +x \
  "$SCRIPT_DIR/start_local_stt.sh" \
  "$SCRIPT_DIR/start_push_to_talk.sh" \
  "$SCRIPT_DIR/toggle_local_stt.sh"

ln -sfn "$SCRIPT_DIR/start_local_stt.sh" "$USER_BIN_DIR/whisperubuntu-daemon"
ln -sfn "$SCRIPT_DIR/start_push_to_talk.sh" "$USER_BIN_DIR/whisperubuntu-push-to-talk"
ln -sfn "$SCRIPT_DIR/toggle_local_stt.sh" "$USER_BIN_DIR/whisperubuntu-toggle"

cp "$SCRIPT_DIR/local-stt.service" "$USER_SYSTEMD_DIR/local-stt.service"
cp "$SCRIPT_DIR/push-to-talk.service" "$USER_SYSTEMD_DIR/push-to-talk.service"

systemctl --user daemon-reload

cat <<EOF
Installed:
  $USER_SYSTEMD_DIR/local-stt.service
  $USER_SYSTEMD_DIR/push-to-talk.service

Linked launchers:
  $USER_BIN_DIR/whisperubuntu-daemon
  $USER_BIN_DIR/whisperubuntu-push-to-talk
  $USER_BIN_DIR/whisperubuntu-toggle

Next steps:
  systemctl --user start local-stt.service
  systemctl --user start push-to-talk.service

Or use:
  $USER_BIN_DIR/whisperubuntu-toggle
EOF
