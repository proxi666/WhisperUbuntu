# WhisperUbuntu Manual Toggle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a manual WhisperUbuntu voice input tool that starts and stops with one shell script and uses F8 as a press-once start, press-again stop recording toggle.

**Architecture:** Keep the existing faster-whisper daemon and Unix socket client. Add a direct shell lifecycle controller for manual startup and shutdown, and refactor the keyboard listener so its toggle state can be tested without a real keyboard.

**Tech Stack:** Bash, Python 3.12, `unittest`, `pynput`, `faster-whisper`, `ffmpeg`, X11, PulseAudio or PipeWire Pulse compatibility.

## Global Constraints

The repository will include `whisperubuntu.sh` as the manual lifecycle script.
No login autostart is enabled.
No large application window appears.
Pressing F8 once starts recording.
Pressing F8 again stops recording and types the transcript into the focused app.
Holding F8 does not cause an accidental immediate stop due to key repeat.
The default transcription model is `large-v3-turbo`.
GPU memory is used only while the manual stack is running.
The stopped state leaves no active daemon, listener, or stale runtime lock.
The default output mode is direct typing into the focused application.
Clipboard output is optional because `xclip` may not be installed.

---

## File structure

- Create `whisperubuntu.sh`: the user-facing lifecycle toggle that starts or stops the daemon and listener without requiring systemd autostart.
- Modify `toggle_local_stt.sh`: delegate to `whisperubuntu.sh` so the old entry point still works.
- Modify `start_push_to_talk.sh`: use direct typing by default instead of clipboard plus typing.
- Modify `scripts/push_to_talk_listener.py`: extract testable toggle state and change F8 behavior from hold-to-talk to press-toggle.
- Create `tests/test_push_to_talk_listener.py`: test press-toggle state, repeated-key suppression, and transcript output actions.
- Create `tests/test_whisperubuntu_script.py`: static and shell-level tests for the lifecycle script behavior that do not load the Whisper model.
- Modify `README.md`: document the direct manual script and press-toggle behavior.

---

### Task 1: Press-toggle listener behavior

**Files:**
- Modify: `scripts/push_to_talk_listener.py`
- Create: `tests/test_push_to_talk_listener.py`

**Interfaces:**
- Produces: `ToggleRecorder` class with `handle_press(now: float) -> str | None` and `handle_release(now: float) -> None`.
- Produces: `deliver_transcript(controller: Controller, transcript: str, output_mode: str) -> None`.
- Consumes: existing `run_client(args, command)` and `type_text(controller, text)` functions.

- [ ] **Step 1: Write failing tests**

Create `tests/test_push_to_talk_listener.py` with tests that import `scripts.push_to_talk_listener` after injecting fake `pynput` modules.
The tests should assert that the first press sends `start`, the second press sends `stop`, key release sends nothing, and repeated press events during one physical hold are ignored.

- [ ] **Step 2: Run tests and verify they fail**

Run: `python -m unittest tests.test_push_to_talk_listener -v`
Expected: FAIL because `ToggleRecorder` and `deliver_transcript` do not exist yet.

- [ ] **Step 3: Implement minimal listener refactor**

Add `ToggleRecorder`.
Use it from `main()` so `on_press` toggles between `start` and `stop`.
Use `on_release` only to clear the pressed-key guard.
Add `deliver_transcript()` so transcript delivery is separately testable.
Keep `key_matches()` and the existing client subprocess boundary.

- [ ] **Step 4: Run tests and verify they pass**

Run: `python -m unittest tests.test_push_to_talk_listener -v`
Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add scripts/push_to_talk_listener.py tests/test_push_to_talk_listener.py
git commit -m "Implement F8 toggle listener"
```

---

### Task 2: Manual lifecycle toggle script

**Files:**
- Create: `whisperubuntu.sh`
- Modify: `toggle_local_stt.sh`
- Modify: `start_push_to_talk.sh`
- Create: `tests/test_whisperubuntu_script.py`

**Interfaces:**
- Produces: `./whisperubuntu.sh` as the canonical manual start/stop entry point.
- Produces: runtime PID directory `$XDG_RUNTIME_DIR/whisperubuntu`.
- Produces: durable log directory `~/.local/state/local-stt`.

- [ ] **Step 1: Write failing lifecycle script tests**

Create `tests/test_whisperubuntu_script.py`.
The tests should verify that `whisperubuntu.sh` exists, contains no `systemctl --user start`, creates `$XDG_RUNTIME_DIR/whisperubuntu`, starts `start_local_stt.sh` and `start_push_to_talk.sh`, and stops processes from PID files.

- [ ] **Step 2: Run tests and verify they fail**

Run: `python -m unittest tests.test_whisperubuntu_script -v`
Expected: FAIL because `whisperubuntu.sh` does not exist yet.

- [ ] **Step 3: Implement `whisperubuntu.sh`**

Create a Bash script that:

- resolves the repo root from the script location,
- stores PIDs in `${XDG_RUNTIME_DIR:-/tmp}/whisperubuntu`,
- writes logs to `$HOME/.local/state/local-stt`,
- starts `start_local_stt.sh` in the background,
- waits for `${XDG_RUNTIME_DIR:-/tmp}/local-stt.sock`,
- starts `start_push_to_talk.sh` in the background,
- stops both processes if either PID is currently alive,
- sends `quit` to the daemon client before killing the daemon PID,
- removes stale PID files on stop.

Update `toggle_local_stt.sh` to call `whisperubuntu.sh`.
Update `start_push_to_talk.sh` to pass `--output-mode type`.

- [ ] **Step 4: Run tests and verify they pass**

Run: `python -m unittest tests.test_whisperubuntu_script -v`
Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add whisperubuntu.sh toggle_local_stt.sh start_push_to_talk.sh tests/test_whisperubuntu_script.py
git commit -m "Add manual WhisperUbuntu toggle script"
```

---

### Task 3: Documentation and full verification

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: `./whisperubuntu.sh` from Task 2.
- Produces: README instructions that make the manual script the primary path.

- [ ] **Step 1: Update README**

Document:

- setup with `python3 -m venv .venv`,
- dependency install,
- start or stop with `./whisperubuntu.sh`,
- F8 press once to start recording and press again to stop,
- no login autostart,
- systemd services as optional legacy helpers.

- [ ] **Step 2: Run unit tests**

Run: `python -m unittest discover -v`
Expected: PASS.

- [ ] **Step 3: Run shell syntax checks**

Run: `bash -n whisperubuntu.sh toggle_local_stt.sh start_local_stt.sh start_push_to_talk.sh`
Expected: exit 0.

- [ ] **Step 4: Run non-model smoke checks**

Run: `./whisperubuntu.sh status`
Expected: prints inactive status and exits 0 without loading the model.

- [ ] **Step 5: Commit**

Run:

```bash
git add README.md
git commit -m "Document manual WhisperUbuntu workflow"
```

---

## Self-review

The plan covers the design spec requirements for manual lifecycle, F8 toggle behavior, no login autostart, direct typing by default, and no large window.
The plan avoids new GUI dependencies and uses the existing faster-whisper daemon.
The plan includes tests before implementation for Python behavior and script behavior.
The plan keeps systemd as optional legacy support while making `whisperubuntu.sh` the default path.
