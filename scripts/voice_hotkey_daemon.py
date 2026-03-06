#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import signal
import socket
import subprocess
import tempfile
import threading
import time
from pathlib import Path

from faster_whisper import WhisperModel


def default_socket_path() -> Path:
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
    if runtime_dir:
        return Path(runtime_dir) / "local-stt.sock"
    return Path("/tmp/local-stt.sock")


class VoiceDaemon:
    def __init__(
        self,
        model_name: str,
        socket_path: Path,
        recordings_dir: Path,
        transcript_log: Path,
        pulse_input: str,
        compute_type: str,
    ) -> None:
        self.socket_path = socket_path
        self.recordings_dir = recordings_dir
        self.transcript_log = transcript_log
        self.pulse_input = pulse_input
        self.compute_type = compute_type
        self.model_name = self.resolve_model_name(model_name)
        self.model = WhisperModel(self.model_name, device="cuda", compute_type=compute_type)
        self.record_proc: subprocess.Popen[str] | None = None
        self.recording_path: Path | None = None
        self.lock = threading.Lock()
        self.is_transcribing = False
        self.last_transcript = ""

    def resolve_model_name(self, model_name: str) -> str:
        local_candidates = [
            Path("models/faster-whisper-large-v3-turbo-lfs"),
            Path("models/faster-whisper-large-v3-turbo"),
        ]
        if model_name == "large-v3-turbo":
            for candidate in local_candidates:
                if (candidate / "model.bin").exists():
                    return str(candidate)
        return model_name

    def start_recording(self) -> dict[str, object]:
        with self.lock:
            if self.is_transcribing:
                return {"ok": False, "state": "busy", "message": "transcription in progress"}
            if self.record_proc is not None:
                return {"ok": False, "state": "recording", "message": "already recording"}

            self.recordings_dir.mkdir(parents=True, exist_ok=True)
            fd, raw_path = tempfile.mkstemp(prefix="take-", suffix=".wav", dir=self.recordings_dir)
            os.close(fd)
            recording_path = Path(raw_path)
            cmd = [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-f",
                "pulse",
                "-i",
                self.pulse_input,
                "-ac",
                "1",
                "-ar",
                "16000",
                str(recording_path),
            ]
            self.record_proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
            )
            self.recording_path = recording_path
            return {"ok": True, "state": "recording", "message": "recording started"}

    def stop_recording(self) -> dict[str, object]:
        with self.lock:
            proc = self.record_proc
            recording_path = self.recording_path
            if proc is None or recording_path is None:
                return {"ok": False, "state": "idle", "message": "not recording"}
            self.record_proc = None
            self.recording_path = None
            self.is_transcribing = True

        try:
            proc.send_signal(signal.SIGINT)
            proc.wait(timeout=10)
        except Exception:
            proc.kill()
            proc.wait(timeout=5)

        try:
            segments, _ = self.model.transcribe(
                str(recording_path),
                language="en",
                beam_size=5,
                vad_filter=True,
            )
            text = " ".join(segment.text.strip() for segment in segments if segment.text.strip()).strip()
            self.last_transcript = text
            self.append_transcript(text, recording_path)
            return {
                "ok": True,
                "state": "idle",
                "message": "transcription complete",
                "transcript": text,
                "audio_file": str(recording_path),
            }
        finally:
            with self.lock:
                self.is_transcribing = False

    def append_transcript(self, text: str, recording_path: Path) -> None:
        self.transcript_log.parent.mkdir(parents=True, exist_ok=True)
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with self.transcript_log.open("a", encoding="utf-8") as handle:
            handle.write(f"[{timestamp}] {recording_path.name}\n")
            handle.write(text + "\n\n")

    def status(self) -> dict[str, object]:
        with self.lock:
            if self.is_transcribing:
                state = "busy"
            elif self.record_proc is not None:
                state = "recording"
            else:
                state = "idle"
        return {"ok": True, "state": state, "last_transcript": self.last_transcript}

    def handle_command(self, payload: dict[str, object]) -> dict[str, object]:
        command = payload.get("command")
        if command == "toggle":
            status = self.status()["state"]
            if status == "recording":
                return self.stop_recording()
            return self.start_recording()
        if command == "start":
            return self.start_recording()
        if command == "stop":
            return self.stop_recording()
        if command == "status":
            return self.status()
        if command == "quit":
            return {"ok": True, "state": "exiting", "message": "daemon exiting"}
        return {"ok": False, "message": f"unknown command: {command}"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Warm GPU push-to-talk daemon")
    parser.add_argument("--model", default="large-v3-turbo")
    parser.add_argument("--compute-type", default="float16")
    parser.add_argument("--socket-path", type=Path, default=default_socket_path())
    parser.add_argument(
        "--recordings-dir",
        type=Path,
        default=Path.home() / ".local" / "state" / "local-stt" / "recordings",
    )
    parser.add_argument(
        "--transcript-log",
        type=Path,
        default=Path.home() / ".local" / "state" / "local-stt" / "transcripts.log",
    )
    parser.add_argument("--pulse-input", default="default")
    return parser.parse_args()


def recv_json(conn: socket.socket) -> dict[str, object]:
    data = b""
    while True:
        chunk = conn.recv(4096)
        if not chunk:
            break
        data += chunk
    if not data:
        return {}
    return json.loads(data.decode("utf-8"))


def send_json(conn: socket.socket, payload: dict[str, object]) -> None:
    conn.sendall(json.dumps(payload, ensure_ascii=False).encode("utf-8"))


def main() -> int:
    args = parse_args()
    if args.socket_path.exists():
        args.socket_path.unlink()

    daemon = VoiceDaemon(
        model_name=args.model,
        socket_path=args.socket_path,
        recordings_dir=args.recordings_dir,
        transcript_log=args.transcript_log,
        pulse_input=args.pulse_input,
        compute_type=args.compute_type,
    )

    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
        server.bind(str(args.socket_path))
        os.chmod(args.socket_path, 0o600)
        server.listen()

        while True:
            conn, _ = server.accept()
            with conn:
                request = recv_json(conn)
                response = daemon.handle_command(request)
                send_json(conn, response)
                if request.get("command") == "quit":
                    break

    if args.socket_path.exists():
        args.socket_path.unlink()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
