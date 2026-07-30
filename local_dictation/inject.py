"""Insert text at the cursor of the frontmost app: clipboard + synthetic ⌘V.

The previous clipboard contents are restored afterwards so dictation
doesn't clobber whatever the user had copied.
"""

import subprocess
import time

from pynput.keyboard import Controller, Key

_kb = Controller()


def _get_clipboard() -> str | None:
    # NSPasteboard directly: pbpaste spawns a subprocess (~45ms measured),
    # paid on every dictation before the paste can happen.
    try:
        from AppKit import NSPasteboard, NSPasteboardTypeString

        text = NSPasteboard.generalPasteboard().stringForType_(NSPasteboardTypeString)
        return str(text) if text is not None else ""
    except Exception:
        pass
    try:
        return subprocess.run(
            ["pbpaste"], capture_output=True, text=True, timeout=5
        ).stdout
    except (subprocess.SubprocessError, OSError):
        return None


def _set_clipboard(text: str):
    try:
        from AppKit import NSPasteboard, NSPasteboardTypeString

        pb = NSPasteboard.generalPasteboard()
        pb.clearContents()
        if pb.setString_forType_(text, NSPasteboardTypeString):
            return
    except Exception:
        pass
    subprocess.run(["pbcopy"], input=text, text=True, timeout=5)


def inject(text: str):
    if not text:
        return
    previous = _get_clipboard()
    _set_clipboard(text)
    time.sleep(0.05)  # let the pasteboard settle before pasting
    with _kb.pressed(Key.cmd):
        _kb.press("v")
        _kb.release("v")
    if previous is not None:
        time.sleep(0.3)  # target app must read the pasteboard before restore
        _set_clipboard(previous)
