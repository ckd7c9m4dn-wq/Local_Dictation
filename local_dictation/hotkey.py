"""Global hold-to-talk hotkey listener.

Hold the configured key to record, release to transcribe. Requires the
host process (your terminal) to have Accessibility / Input Monitoring
permission in System Settings > Privacy & Security.

The press/release callbacks passed in are NEVER run on pynput's event-tap
thread: macOS silently disables an event tap whose callback stalls for
~1 second (kCGEventTapDisabledByTimeout, which pynput does not recover
from), killing the hotkey until the app is restarted. Opening the mic
after idle can take that long, so all work is handed to a dispatch thread
and the tap callback returns in microseconds.
"""

import queue
import threading
from collections.abc import Callable

from pynput import keyboard

KEY_MAP = {
    "alt_r": keyboard.Key.alt_r,
    "alt_l": keyboard.Key.alt_l,
    "cmd_r": keyboard.Key.cmd_r,
    "ctrl_r": keyboard.Key.ctrl_r,
    "f13": getattr(keyboard.Key, "f13", keyboard.Key.alt_r),
}

KEY_LABELS = {
    "alt_r": "Right Option",
    "alt_l": "Left Option",
    "cmd_r": "Right Command",
    "ctrl_r": "Right Control",
    "f13": "F13",
}


class HoldToTalk:
    def __init__(self, key_name: str, on_start: Callable, on_stop: Callable):
        self._key = KEY_MAP.get(key_name, keyboard.Key.alt_r)
        self._on_start = on_start
        self._on_stop = on_stop
        self._held = False
        self._listener: keyboard.Listener | None = None
        self._events: queue.Queue = queue.Queue()

    def start(self):
        threading.Thread(target=self._dispatch, daemon=True).start()
        self._listener = keyboard.Listener(
            on_press=self._press, on_release=self._release
        )
        self._listener.start()

    def stop(self):
        if self._listener:
            self._listener.stop()
            self._listener = None
        self._events.put(None)  # end the dispatch thread

    def _dispatch(self):
        """Run start/stop callbacks off the event-tap thread, in order."""
        while (callback := self._events.get()) is not None:
            try:
                callback()
            except Exception:
                pass  # a failed callback must not kill hotkey dispatch

    def _press(self, key):
        if key == self._key and not self._held:
            self._held = True
            self._events.put(self._on_start)

    def _release(self, key):
        if key == self._key and self._held:
            self._held = False
            self._events.put(self._on_stop)
