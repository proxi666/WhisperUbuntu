# WhisperUbuntu

Local manual voice input for Ubuntu coding workflows.

`WhisperUbuntu` starts only when you ask for it, keeps a Whisper model warm while active, listens for a global F8 toggle key, transcribes spoken English locally, and sends the result back into the active workflow.
It was built for the specific use case of speaking prompts into coding tools such as Codex inside VS Code without depending on a cloud speech API.

Tested on Ubuntu-style desktop workflows with X11 and NVIDIA GPU inference.

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

## Quick Start

```bash
git clone https://github.com/proxi666/WhisperUbuntu.git
cd WhisperUbuntu
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
bash ./whisperubuntu.sh
```

Once running:

- press `F8` once to start recording
- press `F8` again to stop recording
- the transcript is typed back into the focused window

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
- optional `xclip` for clipboard output
- Python 3.12

## Model Used

The actual transcription model is `Whisper large-v3-turbo`, run locally through `faster-whisper` and its converted runtime format. This repository does not introduce a new speech model. What it adds is the workflow layer around that model:

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

- `scripts/`: Python code
- `systemd/`: service unit files
- root-level `.sh` files: user-facing commands

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If your machine does not already have a working NVIDIA driver / CUDA-capable setup, handle that first. Once `nvidia-smi` works and your Python environment is ready, this repo setup is straightforward.

## One-Off File Transcription

```bash
./run-transcribe.sh /path/to/audio.wav --device cuda --compute-type float16 --language en --output transcript.txt --json-output transcript.json
```

## Manual Start/Stop

This project is intentionally configured to stay off by default so VRAM remains available for other workloads.

Start the whole voice input stack manually:

```bash
bash ./whisperubuntu.sh
```

Run the same script again to stop it:

```bash
bash ./whisperubuntu.sh
```

Check whether it is active without loading the model:

```bash
bash ./whisperubuntu.sh status
```

The compatibility wrapper still works and delegates to the same manual script:

```bash
./toggle_local_stt.sh
```

## Optional User Services

The direct `./whisperubuntu.sh` path is the recommended flow.
The systemd user units are still available for people who want service management, but they are optional and are not required for the manual workflow.
They are not enabled for login autostart by default.

Optional install flow:

```bash
./install_user_services.sh
```

This script:

- installs the service units into `~/.config/systemd/user`
- creates launcher symlinks in `~/.local/bin`
- keeps the service files themselves portable
- avoids hardcoding your repo path into the checked-in unit files

Start the optional services:

```bash
systemctl --user start local-stt.service
systemctl --user start push-to-talk.service
```

Stop the optional services:

```bash
systemctl --user stop push-to-talk.service
systemctl --user stop local-stt.service
```

## Notes

- If you move the repo after installing the launchers, rerun `./install_user_services.sh`.
- `large-v3-turbo` was chosen because it gives strong quality with lower latency and lower VRAM cost than `large-v3`.
- This project is tuned for Ubuntu and X11. It is not a generic cross-platform voice layer yet.

## Limitations

- tuned for Ubuntu and X11 rather than being fully cross-platform
- assumes a working NVIDIA/CUDA stack if you want GPU inference
- clipboard behavior can vary by desktop session, so direct typing is the primary handoff path
- if another application already owns your chosen hotkey, you may need to change `F8`

## Future Improvements

- Better clipboard integration across desktop environments
- Optional direct submit to the active prompt
- Configurable model and language settings
- Wayland support
- Cleaner packaging for reuse on other Ubuntu machines

## License

MIT
