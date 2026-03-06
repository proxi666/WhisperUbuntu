#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

from pynput import keyboard
from pynput.keyboard import Controller


def default_socket_path() -> Path:
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
    if runtime_dir:
        return Path(runtime_dir) / "local-stt.sock"
    return Path("/tmp/local-stt.sock")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Hold a global key to record, release to transcribe and copy"
    )
    parser.add_argument(
        "--key",
        default="f8",
        help="Global key to hold, e.g. f8, f9, pause, scroll_lock",
    )
    parser.add_argument("--socket-path", type=Path, default=default_socket_path())
    parser.add_argument(
        "--client",
        type=Path,
        default=Path(__file__).with_name("voice_hotkey_client.py"),
        help="Path to the STT client script",
    )
    parser.add_argument(
        "--python",
        type=Path,
        default=Path(sys.executable),
        help="Python interpreter to use for the client",
    )
    parser.add_argument(
        "--output-mode",
        choices=["type", "clipboard", "both"],
        default="both",
        help="What to do with the transcript after release",
    )
    return parser.parse_args()


def normalize_key(name: str) -> str:
    return name.strip().lower().replace("-", "_").replace(" ", "_")


def key_matches(key: keyboard.Key | keyboard.KeyCode, target: str) -> bool:
    if isinstance(key, keyboard.KeyCode):
        return normalize_key(key.char or "") == target
    key_name = getattr(key, "name", None)
    if key_name:
        return normalize_key(key_name) == target
    return normalize_key(str(key).split(".")[-1]) == target


def run_client(
    args: argparse.Namespace,
    command: str,
    copy: bool = False,
) -> subprocess.CompletedProcess[str]:
    cmd = [
        str(args.python),
        str(args.client),
        command,
        "--socket-path",
        str(args.socket_path),
    ]
    if copy:
        cmd.append("--copy")
    return subprocess.run(cmd, capture_output=True, text=True)


def copy_to_clipboard(text: str) -> None:
    proc = subprocess.Popen(
        ["xclip", "-selection", "clipboard", "-loops", "1"],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
        start_new_session=True,
    )
    assert proc.stdin is not None
    proc.stdin.write(text)
    proc.stdin.close()


def type_text(controller: Controller, text: str) -> None:
    controller.type(text)


def main() -> int:
    args = parse_args()
    target = normalize_key(args.key)
    held = False
    last_event = 0.0
    controller = Controller()

    if not args.socket_path.exists():
        print(f"Socket not found: {args.socket_path}", file=sys.stderr)
        return 1

    print(f"Push-to-talk ready on key: {target}")

    def on_press(key: keyboard.Key | keyboard.KeyCode) -> None:
        nonlocal held, last_event
        if held or not key_matches(key, target):
            return
        now = time.monotonic()
        if now - last_event < 0.15:
            return
        last_event = now
        result = run_client(args, "start")
        if result.returncode == 0:
            held = True
            print("recording...")
        elif result.stdout:
            print(result.stdout.strip(), file=sys.stderr)
        elif result.stderr:
            print(result.stderr.strip(), file=sys.stderr)

    def on_release(key: keyboard.Key | keyboard.KeyCode) -> None:
        nonlocal held, last_event
        if not held or not key_matches(key, target):
            return
        now = time.monotonic()
        if now - last_event < 0.15:
            return
        last_event = now
        held = False
        result = run_client(args, "stop")
        transcript = result.stdout.strip()
        if result.returncode == 0 and transcript:
            if args.output_mode in {"clipboard", "both"}:
                try:
                    copy_to_clipboard(transcript)
                except Exception:
                    pass
            if args.output_mode in {"type", "both"}:
                # Small delay avoids racing the key release with the typed output.
                time.sleep(0.05)
                type_text(controller, transcript)
            print(transcript)
        elif result.stderr:
            print(result.stderr.strip(), file=sys.stderr)

    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
