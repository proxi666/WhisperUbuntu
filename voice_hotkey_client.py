#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
from subprocess import PIPE, DEVNULL
from pathlib import Path


def default_socket_path() -> Path:
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
    if runtime_dir:
        return Path(runtime_dir) / "local-stt.sock"
    return Path("/tmp/local-stt.sock")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Control the local STT daemon")
    parser.add_argument(
        "command",
        choices=["toggle", "start", "stop", "status", "quit"],
        help="Command to send to the daemon",
    )
    parser.add_argument("--socket-path", type=Path, default=default_socket_path())
    parser.add_argument(
        "--copy",
        action="store_true",
        help="Copy transcript responses to the X11 clipboard with xclip",
    )
    return parser.parse_args()


def copy_to_clipboard(text: str) -> None:
    proc = subprocess.Popen(
        ["xclip", "-selection", "clipboard", "-loops", "1"],
        stdin=PIPE,
        stdout=DEVNULL,
        stderr=DEVNULL,
        text=True,
        start_new_session=True,
    )
    assert proc.stdin is not None
    proc.stdin.write(text)
    proc.stdin.close()


def main() -> int:
    args = parse_args()
    if not args.socket_path.exists():
        print(f"Socket not found: {args.socket_path}", file=sys.stderr)
        print("Start the daemon first.", file=sys.stderr)
        return 1

    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.connect(str(args.socket_path))
        client.sendall(json.dumps({"command": args.command}).encode("utf-8"))
        client.shutdown(socket.SHUT_WR)
        response = json.loads(client.recv(1 << 20).decode("utf-8"))

    transcript = response.get("transcript")
    if transcript:
        if args.copy:
            copy_to_clipboard(str(transcript))
        print(transcript)
    else:
        print(json.dumps(response, ensure_ascii=False))
    return 0 if response.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
