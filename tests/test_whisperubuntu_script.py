from __future__ import annotations

import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "whisperubuntu.sh"


class WhisperUbuntuScriptTests(unittest.TestCase):
    def test_manual_toggle_script_exists(self) -> None:
        self.assertTrue(SCRIPT.exists())

    def test_script_does_not_start_systemd_user_services(self) -> None:
        text = SCRIPT.read_text(encoding="utf-8")

        self.assertNotIn("systemctl --user start", text)
        self.assertNotIn("systemctl --user enable", text)

    def test_script_uses_runtime_pid_directory_and_local_state_logs(self) -> None:
        text = SCRIPT.read_text(encoding="utf-8")

        self.assertIn("whisperubuntu", text)
        self.assertIn("local-stt", text)
        self.assertIn("daemon.pid", text)
        self.assertIn("listener.pid", text)

    def test_script_starts_daemon_before_listener(self) -> None:
        text = SCRIPT.read_text(encoding="utf-8")

        daemon_index = text.index("start_local_stt.sh")
        listener_index = text.index("start_push_to_talk.sh")
        self.assertLess(daemon_index, listener_index)

    def test_script_stops_daemon_with_client_quit_and_pid_cleanup(self) -> None:
        text = SCRIPT.read_text(encoding="utf-8")

        self.assertIn("voice_hotkey_client.py", text)
        self.assertIn("quit", text)
        self.assertIn("rm -f", text)

    def test_status_reports_inactive_without_loading_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            env = os.environ.copy()
            env["XDG_RUNTIME_DIR"] = tmpdir
            env["HOME"] = tmpdir

            result = subprocess.run(
                [str(SCRIPT), "status"],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=5,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("inactive", result.stdout.lower())

    def test_first_model_start_timeout_allows_slow_warmup(self) -> None:
        text = SCRIPT.read_text(encoding="utf-8")
        match = re.search(r"DAEMON_START_TIMEOUT_SECONDS=(\d+)", text)

        self.assertIsNotNone(match)
        assert match is not None
        self.assertGreaterEqual(int(match.group(1)), 180)


if __name__ == "__main__":
    unittest.main()
