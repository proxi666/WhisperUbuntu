# WhisperUbuntu

Local push-to-talk voice input for Ubuntu coding workflows.

`WhisperUbuntu` keeps a Whisper model warm on GPU, listens for a global hold-to-talk key, transcribes spoken English locally, and sends the result back into the active workflow. It was built for the specific use case of speaking prompts into coding tools such as Codex inside VS Code without depending on a cloud speech API.

## Assumptions

This project is aimed at a Linux user who is already on Ubuntu, ideally Ubuntu 22.04 or a similar setup.

The README assumes you already have the core machine-level pieces working:

- Ubuntu with a normal desktop session
- X11 session, not Wayland
- an NVIDIA GPU if you want GPU inference
- working NVIDIA driver stack
- a CUDA-compatible runtime environment that your local inference stack can actually use
- `systemd --user`
- PulseAudio or PipeWire with Pulse compatibility

In practical terms, before using this repo, you should already be able to confirm things like:

```bash
nvidia-smi
python3 --version
systemctl --user status
```

This repo is not trying to be a full "fresh Ubuntu machine bootstrap" guide. The goal here is the voice workflow itself, not the entire CUDA or driver installation story.

## What It Does

- Runs local speech-to-text with `faster-whisper`
- Keeps the model resident on GPU for low-latency transcription
- Uses a global push-to-talk key on Ubuntu/X11
- Forces English transcription for dictation-style usage
- Types text back into the focused window and also supports clipboard-style flow
- Lets you start and stop the whole setup manually to control VRAM usage

## Why This Exists

Existing voice input tools on Windows and macOS are easier to find. On Ubuntu, the missing piece was not the model itself, but the end-to-end workflow:

- microphone capture
- warm local inference
- global key handling
- direct text handoff into the editor
- manual resource control

This project ties those pieces together into one practical local dictation loop.

## Current Stack

- Ubuntu
- X11
- `systemd --user`
- PulseAudio or PipeWire via Pulse compatibility
- `faster-whisper`
- `Whisper large-v3-turbo`
- `xclip`
- Python 3.12

## Model Used


The actual transcription model is `Whisper large-v3-turbo`, run locally through `faster-whisper` and its converted runtime format. What this project adds is the workflow layer around that model:

- microphone capture
- warm GPU daemon
- global hotkey handling
- user services
- direct text handoff back into the active coding workflow


## GPU Usage

With the default `large-v3-turbo` setup in this project, a reasonable expectation is roughly **~2 GB of VRAM** while the service is active, with some variation depending on driver stack, runtime state, and hardware.

In other words:

- this is light enough to be practical on an 8 GB GPU
- it still uses enough VRAM that manual start/stop control is useful
- this is one reason `large-v3-turbo` was chosen instead of a heavier model

## Behavior

Default workflow:

- Press `F8` once to start recording
- Press `F8` again to stop recording
- Transcription runs locally on GPU
- Output is typed back into the active window
- Clipboard copy is treated as a secondary best-effort path


## Repository Layout

- `voice_hotkey_daemon.py`: warm GPU daemon that records and transcribes
- `push_to_talk_listener.py`: global hold-to-talk listener
- `voice_hotkey_client.py`: control client for the daemon socket
- `install_user_services.sh`: installs portable user services and launcher symlinks
- `start_local_stt.sh`: repo-local launcher for the daemon
- `start_push_to_talk.sh`: repo-local launcher for the hotkey listener
- `toggle_local_stt.sh`: start/stop toggle for the user services
- `local-stt.service`: user service for the transcription daemon
- `push-to-talk.service`: user service for the hotkey listener
- `transcribe.py`: one-off file transcription CLI

## Setup

```bash
cd local-stt
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If your machine does not already have a working NVIDIA driver / CUDA-capable setup, handle that first. Once `nvidia-smi` works and your Python environment is ready, this repo setup is straightforward.

## One-Off File Transcription

```bash
source .venv/bin/activate
python transcribe.py /path/to/audio.wav --device cuda --compute-type float16 --language en --output transcript.txt --json-output transcript.json
```

## Manual Start/Stop

This project is intentionally configured to stay off by default so VRAM remains available for other workloads.

Install the user services first:

```bash
./install_user_services.sh
```

Start or stop both services with:

```bash
./toggle_local_stt.sh
```

## User Services

Recommended install flow:

```bash
./install_user_services.sh
```

This script:

- installs the service units into `~/.config/systemd/user`
- creates launcher symlinks in `~/.local/bin`
- keeps the service files themselves portable
- avoids hardcoding your repo path into the checked-in unit files

Start them:

```bash
systemctl --user start local-stt.service
systemctl --user start push-to-talk.service
```

Stop them:

```bash
systemctl --user stop push-to-talk.service
systemctl --user stop local-stt.service
```

## Notes

- If you move the repo after installing the launchers, rerun `./install_user_services.sh`.
- `large-v3-turbo` was chosen because it gives strong quality with lower latency and lower VRAM cost than `large-v3`.
- This project is tuned for Ubuntu and X11. It is not a generic cross-platform voice layer yet.

## Future Improvements

- Better clipboard integration across desktop environments
- Optional direct submit to the active prompt
- Configurable model and language settings
- Wayland support
- Cleaner packaging for reuse on other Ubuntu machines
