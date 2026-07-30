"""Start-at-login support: a LaunchAgent that opens the .app bundle."""

import os
import plistlib
import subprocess
from pathlib import Path

APP_PATH = "/Applications/Local Dictation.app"
AGENT_PATH = Path.home() / "Library" / "LaunchAgents" / "com.mhardy.local-dictation.plist"


def enabled() -> bool:
    return AGENT_PATH.exists()


def enable():
    AGENT_PATH.parent.mkdir(parents=True, exist_ok=True)
    AGENT_PATH.write_bytes(
        plistlib.dumps(
            {
                "Label": "com.mhardy.local-dictation",
                "ProgramArguments": ["/usr/bin/open", "-a", APP_PATH],
                "RunAtLoad": True,
            }
        )
    )


def disable():
    AGENT_PATH.unlink(missing_ok=True)
    subprocess.run(
        ["launchctl", "bootout", f"gui/{os.getuid()}/com.mhardy.local-dictation"],
        capture_output=True,
    )
