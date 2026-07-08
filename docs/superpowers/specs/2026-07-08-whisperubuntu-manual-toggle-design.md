# WhisperUbuntu manual toggle design

## Context

The user wants to use the existing `proxi666/WhisperUbuntu` project instead of the Qt based OpenSuperWhisper Linux prototype.
The desired experience is close to the earlier WhisperUbuntu flow: start it only when needed, speak into the currently focused application, and avoid a large app window.
The machine is an Ubuntu X11 laptop with an NVIDIA RTX 5070 Laptop GPU, so keeping the Whisper model warm is useful while voice input is active but should not happen all day.
The current upstream repository already has the right foundation: a warm faster-whisper daemon, a global F8 listener, local audio recording through Pulse or PipeWire, and direct typing into the focused window.
The current repository documentation describes F8 as a press-once start and press-again stop workflow.
The current listener implementation behaves like hold-to-talk, so it must be changed to match the documented and desired toggle behavior.

## Goals

The project will provide a manual voice input tool for Ubuntu.
The user starts the tool by running one shell script.
The user stops the entire tool by running the same shell script again.
While the tool is running, pressing F8 once starts recording.
While recording, pressing F8 again stops recording, transcribes the audio, and types the transcript into the focused application.
The tool will use faster-whisper with the `large-v3-turbo` model on CUDA when available.
The tool will not open a large history window.
The tool will show only a small transient status indicator when useful.
The tool will not start automatically at login.
The tool will not reserve GPU memory unless the manual script has started it.

## Non-goals

This change will not continue the OpenSuperWhisper Qt window prototype.
This change will not add a full settings window, transcript history window, or tray application.
This change will not add wake word activation.
This change will not make the tool work on Wayland.
This change will not require cloud transcription.
This change will not install a login autostart service by default.

## Approaches considered

### Recommended approach: polish WhisperUbuntu directly

This approach keeps WhisperUbuntu as the primary project and adjusts it to the desired manual workflow.
It keeps the existing daemon, socket client, F8 listener, and faster-whisper model flow.
It adds a single lifecycle toggle script and a tiny indicator instead of a larger GUI.
This is the smallest path that matches the user's real desired UX.

### Hybrid approach: use WhisperUbuntu daemon behind the OpenSuperWhisper UI

This approach would keep WhisperUbuntu for transcription but reuse the newer Qt prototype for UI pieces.
It would add more dependencies and bring back the app-window feeling the user disliked.
It is not selected because the user's main requirement is no visible box or interference.

### Current-port approach: hide the OpenSuperWhisper window

This approach would keep the OpenSuperWhisper Linux port and change it to hide its main window.
It would preserve work already done, but the application model is still centered on a Qt transcript manager.
It is not selected because the WhisperUbuntu architecture already matches manual background voice typing more closely.

## Selected architecture

The selected architecture is a manually controlled background voice input stack.
The stack has three runtime parts: a warm transcription daemon, a keyboard listener, and a tiny status indicator.
The stack is started and stopped through one shell script.
The script is the only normal user entry point.

The daemon owns the Whisper model and audio recording lifecycle.
The listener owns global F8 detection and sends commands to the daemon socket.
The indicator owns tiny, non-interfering user feedback.
The client remains the command boundary between scripts, listener, and daemon.

## Manual lifecycle script

The repository will include `whisperubuntu.sh` as the manual lifecycle script.
When the script is run and WhisperUbuntu is not active, it starts the daemon and the F8 listener in the background.
When the script is run and WhisperUbuntu is active, it stops the listener and daemon cleanly.
The script will store PID files under `$XDG_RUNTIME_DIR/whisperubuntu`.
The script will store durable logs under `~/.local/state/local-stt`.
The script will avoid enabling systemd user autostart by default.
The script may still support systemd service files as optional installation artifacts, but they are not the default behavior.
The script will print a concise status line such as `WhisperUbuntu started` or `WhisperUbuntu stopped`.

## F8 recording behavior

F8 will be a toggle key while the tool is running.
The first press sends `start` to the daemon.
The next press sends `stop` to the daemon.
The listener will ignore key-repeat events so one long physical press does not immediately start and stop recording.
The listener will not require holding F8.
The listener will preserve the current focused application so the final transcript is typed where the user was working.

## Transcription and output behavior

The default model will remain `large-v3-turbo`.
The default device will be CUDA when the local faster-whisper stack can use it.
The default output mode will be direct typing into the focused application.
Clipboard output will be optional because `xclip` is not currently installed on the laptop.
The transcript log can remain as a local debug and history artifact, but it will not be presented in a large window.

## Status indicator behavior

The indicator will be tiny and transient.
It will show a state such as `Listening`, `Transcribing`, `Typed`, or `Failed`.
It will not steal keyboard focus.
It will not stay visible while idle.
It will not behave like a transcript history window.
The implementation should prefer a lightweight local UI path such as Tkinter or desktop notifications over Qt.
If a status indicator proves unreliable on the current desktop, the fallback is `notify-send` for brief state messages.

## Error handling

If the daemon socket is unavailable during startup, the script will report the failure and avoid leaving a half-started listener running.
If model loading fails, the daemon will report a clear error and exit instead of waiting silently.
If recording fails, the listener or daemon will show a failed status and return to idle.
If transcription fails, the tool will not type stale text.
If direct typing fails, the error will be visible in logs and through a brief failure indication.
If the stop script path runs while only one component is alive, it will clean up that component and remove stale PID files.

## Testing strategy

Unit tests will cover F8 toggle state transitions and key-repeat suppression.
Unit tests will cover lifecycle detection for inactive, active, and partially active states.
Unit tests will cover client command handling for `start`, `stop`, `status`, and `quit`.
Manual smoke testing will start the tool through the script, press F8 to record, press F8 again to stop, and verify text appears in a focused editor.
Manual smoke testing will run the script again and verify no daemon, listener, or model GPU allocation remains active.
Manual smoke testing will confirm that no large window appears.
Manual smoke testing will confirm the tiny status indication does not steal focus.

## Rollout plan

The implementation will keep changes additive and focused.
The first milestone will make the manual lifecycle script reliable.
The second milestone will change the listener from hold-to-talk to press-toggle behavior.
The third milestone will add or wire the tiny status feedback.
The fourth milestone will verify the real laptop experience end to end.
The existing OpenSuperWhisper clone will be left untouched unless the user separately asks to remove or disable it.

## Acceptance criteria

Running the shell script once starts WhisperUbuntu.
Running the same shell script again stops WhisperUbuntu.
No login autostart is enabled.
No large application window appears.
Pressing F8 once starts recording.
Pressing F8 again stops recording and types the transcript into the focused app.
Holding F8 does not cause an accidental immediate stop due to key repeat.
The default transcription model is `large-v3-turbo`.
GPU memory is used only while the manual stack is running.
The stopped state leaves no active daemon, listener, or stale runtime lock.
