#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
ROOT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"
RUNTIME_BASE="${XDG_RUNTIME_DIR:-/tmp}"
PID_DIR="$RUNTIME_BASE/whisperubuntu"
SOCKET_PATH="$RUNTIME_BASE/local-stt.sock"
STATE_DIR="$HOME/.local/state/local-stt"
LOG_DIR="$STATE_DIR/logs"
DAEMON_PID_FILE="$PID_DIR/daemon.pid"
LISTENER_PID_FILE="$PID_DIR/listener.pid"
DAEMON_START_TIMEOUT_SECONDS=240

mkdir -p "$PID_DIR" "$LOG_DIR"

python_bin() {
  if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
    echo "$ROOT_DIR/.venv/bin/python"
  else
    echo "python3"
  fi
}

pid_from_file() {
  local pid_file="$1"
  if [[ -f "$pid_file" ]]; then
    tr -dc '0-9' < "$pid_file"
  fi
}

is_running() {
  local pid_file="$1"
  local pid
  pid="$(pid_from_file "$pid_file")"
  if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
    return 0
  fi
  return 1
}

remove_stale_pid() {
  local pid_file="$1"
  if [[ -f "$pid_file" ]] && ! is_running "$pid_file"; then
    rm -f "$pid_file"
  fi
}

wait_for_exit() {
  local pid="$1"
  local label="$2"
  for _ in $(seq 1 20); do
    if ! kill -0 "$pid" 2>/dev/null; then
      return 0
    fi
    sleep 0.1
  done
  echo "$label did not exit after SIGTERM, killing it."
  kill -KILL "$pid" 2>/dev/null || true
}

stop_pid_file() {
  local pid_file="$1"
  local label="$2"
  local pid
  pid="$(pid_from_file "$pid_file")"
  if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
    kill "$pid" 2>/dev/null || true
    wait_for_exit "$pid" "$label"
  fi
  rm -f "$pid_file"
}

send_daemon_quit() {
  if [[ -S "$SOCKET_PATH" ]]; then
    "$(python_bin)" "$ROOT_DIR/scripts/voice_hotkey_client.py" quit --socket-path "$SOCKET_PATH" >/dev/null 2>&1 || true
  fi
}

is_active() {
  remove_stale_pid "$DAEMON_PID_FILE"
  remove_stale_pid "$LISTENER_PID_FILE"
  if is_running "$DAEMON_PID_FILE" || is_running "$LISTENER_PID_FILE"; then
    return 0
  fi
  return 1
}

status() {
  if is_active; then
    echo "WhisperUbuntu active"
    if is_running "$DAEMON_PID_FILE"; then
      echo "daemon: running pid $(pid_from_file "$DAEMON_PID_FILE")"
    else
      echo "daemon: inactive"
    fi
    if is_running "$LISTENER_PID_FILE"; then
      echo "listener: running pid $(pid_from_file "$LISTENER_PID_FILE")"
    else
      echo "listener: inactive"
    fi
  else
    echo "WhisperUbuntu inactive"
  fi
}

wait_for_socket() {
  for _ in $(seq 1 "$DAEMON_START_TIMEOUT_SECONDS"); do
    if [[ -S "$SOCKET_PATH" ]]; then
      return 0
    fi
    if [[ -f "$DAEMON_PID_FILE" ]] && ! is_running "$DAEMON_PID_FILE"; then
      echo "WhisperUbuntu daemon exited before the socket became ready."
      tail -n 40 "$LOG_DIR/daemon.log" 2>/dev/null || true
      return 1
    fi
    sleep 1
  done
  echo "Timed out waiting for daemon socket: $SOCKET_PATH"
  tail -n 40 "$LOG_DIR/daemon.log" 2>/dev/null || true
  return 1
}

start_all() {
  remove_stale_pid "$DAEMON_PID_FILE"
  remove_stale_pid "$LISTENER_PID_FILE"
  if is_active; then
    echo "WhisperUbuntu already active."
    status
    return 0
  fi

  echo "Starting WhisperUbuntu..."
  nohup "$ROOT_DIR/start_local_stt.sh" > "$LOG_DIR/daemon.log" 2>&1 &
  echo "$!" > "$DAEMON_PID_FILE"

  if ! wait_for_socket; then
    stop_pid_file "$DAEMON_PID_FILE" "daemon"
    rm -f "$SOCKET_PATH"
    return 1
  fi

  nohup "$ROOT_DIR/start_push_to_talk.sh" > "$LOG_DIR/listener.log" 2>&1 &
  echo "$!" > "$LISTENER_PID_FILE"

  echo "WhisperUbuntu started."
  echo "Press F8 once to record, then press F8 again to transcribe and type."
}

stop_all() {
  remove_stale_pid "$DAEMON_PID_FILE"
  remove_stale_pid "$LISTENER_PID_FILE"
  if ! is_active; then
    rm -f "$DAEMON_PID_FILE" "$LISTENER_PID_FILE"
    echo "WhisperUbuntu already inactive."
    return 0
  fi

  echo "Stopping WhisperUbuntu..."
  stop_pid_file "$LISTENER_PID_FILE" "listener"
  send_daemon_quit
  stop_pid_file "$DAEMON_PID_FILE" "daemon"
  rm -f "$SOCKET_PATH" "$DAEMON_PID_FILE" "$LISTENER_PID_FILE"
  echo "WhisperUbuntu stopped."
}

command="${1:-toggle}"
case "$command" in
  start)
    start_all
    ;;
  stop)
    stop_all
    ;;
  restart)
    stop_all
    start_all
    ;;
  status)
    status
    ;;
  toggle)
    if is_active; then
      stop_all
    else
      start_all
    fi
    ;;
  *)
    echo "Usage: $0 [start|stop|restart|status|toggle]" >&2
    exit 2
    ;;
esac
