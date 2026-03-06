#!/usr/bin/env bash
set -euo pipefail

LOCAL_STT_SERVICE="local-stt.service"
PUSH_TO_TALK_SERVICE="push-to-talk.service"

if systemctl --user is-active --quiet "$LOCAL_STT_SERVICE" || systemctl --user is-active --quiet "$PUSH_TO_TALK_SERVICE"; then
  echo "Stopping local speech-to-text services..."
  systemctl --user stop "$PUSH_TO_TALK_SERVICE" "$LOCAL_STT_SERVICE"
  echo "Stopped:"
  systemctl --user --no-pager --plain --full status "$LOCAL_STT_SERVICE" "$PUSH_TO_TALK_SERVICE" | sed -n '1,20p'
else
  echo "Starting local speech-to-text services..."
  systemctl --user start "$LOCAL_STT_SERVICE"
  systemctl --user start "$PUSH_TO_TALK_SERVICE"
  echo "Started:"
  systemctl --user --no-pager --plain --full status "$LOCAL_STT_SERVICE" "$PUSH_TO_TALK_SERVICE" | sed -n '1,20p'
fi
