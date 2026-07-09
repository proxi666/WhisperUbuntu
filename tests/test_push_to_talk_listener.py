from __future__ import annotations

import sys
import types
import unittest
from unittest import mock


def install_fake_pynput() -> None:
    pynput_module = types.ModuleType("pynput")
    keyboard_module = types.ModuleType("pynput.keyboard")

    class FakeKey:
        pass

    class FakeKeyCode:
        def __init__(self, char: str | None = None) -> None:
            self.char = char

    class FakeController:
        def __init__(self) -> None:
            self.typed: list[str] = []

        def type(self, text: str) -> None:
            self.typed.append(text)

    class FakeListener:
        def __init__(self, *args: object, **kwargs: object) -> None:
            self.args = args
            self.kwargs = kwargs

        def __enter__(self) -> "FakeListener":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def join(self) -> None:
            return None

    keyboard_module.Key = FakeKey
    keyboard_module.KeyCode = FakeKeyCode
    keyboard_module.Controller = FakeController
    keyboard_module.Listener = FakeListener
    pynput_module.keyboard = keyboard_module

    sys.modules["pynput"] = pynput_module
    sys.modules["pynput.keyboard"] = keyboard_module


install_fake_pynput()

from scripts import push_to_talk_listener as listener


class ToggleRecorderTests(unittest.TestCase):
    def test_first_press_starts_and_next_physical_press_stops(self) -> None:
        recorder = listener.ToggleRecorder(debounce_seconds=0.15)

        self.assertEqual(recorder.handle_press(1.00), "start")
        recorder.handle_release(1.05)
        self.assertEqual(recorder.handle_press(2.00), "stop")

    def test_release_does_not_send_a_command(self) -> None:
        recorder = listener.ToggleRecorder(debounce_seconds=0.15)

        self.assertEqual(recorder.handle_press(1.00), "start")

        self.assertIsNone(recorder.handle_release(1.05))

    def test_repeated_press_events_during_one_hold_are_ignored(self) -> None:
        recorder = listener.ToggleRecorder(debounce_seconds=0.15)

        self.assertEqual(recorder.handle_press(1.00), "start")
        self.assertIsNone(recorder.handle_press(1.01))
        self.assertIsNone(recorder.handle_press(1.20))
        recorder.handle_release(1.25)
        self.assertEqual(recorder.handle_press(2.00), "stop")

    def test_debounce_ignores_too_fast_second_physical_press(self) -> None:
        recorder = listener.ToggleRecorder(debounce_seconds=0.15)

        self.assertEqual(recorder.handle_press(1.00), "start")
        recorder.handle_release(1.01)

        self.assertIsNone(recorder.handle_press(1.05))


class DeliverTranscriptTests(unittest.TestCase):
    def test_type_mode_types_transcript_without_clipboard(self) -> None:
        controller = object()

        with mock.patch.object(listener, "type_text") as type_text, mock.patch.object(
            listener, "copy_to_clipboard"
        ) as copy_to_clipboard:
            listener.deliver_transcript(controller, "hello world", "type")

        type_text.assert_called_once_with(controller, "hello world")
        copy_to_clipboard.assert_not_called()

    def test_both_mode_still_types_when_clipboard_fails(self) -> None:
        controller = object()

        with mock.patch.object(listener, "type_text") as type_text, mock.patch.object(
            listener, "copy_to_clipboard", side_effect=RuntimeError("missing xclip")
        ):
            listener.deliver_transcript(controller, "hello world", "both")

        type_text.assert_called_once_with(controller, "hello world")


if __name__ == "__main__":
    unittest.main()
