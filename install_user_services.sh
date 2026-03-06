#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
USER_SYSTEMD_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
USER_BIN_DIR="$HOME/.local/bin"

mkdir -p "$USER_SYSTEMD_DIR" "$USER_BIN_DIR"

chmod +x \
  "$SCRIPT_DIR/install_user_services.sh" \
  "$SCRIPT_DIR/bin/dictate" \
  "$SCRIPT_DIR/bin/run-transcribe.sh" \
  "$SCRIPT_DIR/bin/start_local_stt.sh" \
  "$SCRIPT_DIR/bin/start_push_to_talk.sh" \
  "$SCRIPT_DIR/bin/toggle_local_stt.sh"

ln -sfn "$SCRIPT_DIR/bin/start_local_stt.sh" "$USER_BIN_DIR/whisperubuntu-daemon"
ln -sfn "$SCRIPT_DIR/bin/start_push_to_talk.sh" "$USER_BIN_DIR/whisperubuntu-push-to-talk"
ln -sfn "$SCRIPT_DIR/bin/toggle_local_stt.sh" "$USER_BIN_DIR/whisperubuntu-toggle"
ln -sfn "$SCRIPT_DIR/bin/run-transcribe.sh" "$USER_BIN_DIR/whisperubuntu-transcribe"
ln -sfn "$SCRIPT_DIR/bin/dictate" "$USER_BIN_DIR/whisperubuntu-client"

cp "$SCRIPT_DIR/systemd/local-stt.service" "$USER_SYSTEMD_DIR/local-stt.service"
cp "$SCRIPT_DIR/systemd/push-to-talk.service" "$USER_SYSTEMD_DIR/push-to-talk.service"

systemctl --user daemon-reload

cat <<EOF
Installed:
  $USER_SYSTEMD_DIR/local-stt.service
  $USER_SYSTEMD_DIR/push-to-talk.service

Linked launchers:
  $USER_BIN_DIR/whisperubuntu-daemon
  $USER_BIN_DIR/whisperubuntu-push-to-talk
  $USER_BIN_DIR/whisperubuntu-toggle
  $USER_BIN_DIR/whisperubuntu-transcribe
  $USER_BIN_DIR/whisperubuntu-client

Next steps:
  systemctl --user start local-stt.service
  systemctl --user start push-to-talk.service

Or use:
  $USER_BIN_DIR/whisperubuntu-toggle
EOF
