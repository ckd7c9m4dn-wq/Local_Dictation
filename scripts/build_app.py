"""Build and install "Local Dictation.app". Run inside the venv:

    python scripts/build_app.py

Creates a menu-bar-only app bundle whose executable is a stub that runs
the venv's local-dictation entry point, renders a 🎤 icon, ad-hoc signs the
bundle for a stable TCC identity, and installs it to /Applications.
"""

import plistlib
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
BUNDLE_ID = "com.mhardy.local-dictation"
APP_NAME = "Local Dictation"
DIST = PROJECT / "dist" / f"{APP_NAME}.app"
INSTALL = Path("/Applications") / f"{APP_NAME}.app"

INFO_PLIST = {
    "CFBundleName": APP_NAME,
    "CFBundleDisplayName": APP_NAME,
    "CFBundleIdentifier": BUNDLE_ID,
    "CFBundleVersion": "0.1.0",
    "CFBundleShortVersionString": "0.1.0",
    "CFBundlePackageType": "APPL",
    "CFBundleExecutable": "local-dictation",
    "CFBundleIconFile": "AppIcon",
    "LSUIElement": True,  # menu-bar only: no Dock icon, no app switcher entry
    "LSMinimumSystemVersion": "14.0",
    "NSMicrophoneUsageDescription": "Local Dictation records your voice to transcribe it, entirely on this Mac.",
    "NSHighResolutionCapable": True,
}

LAUNCHER_SRC = PROJECT / "scripts" / "launcher.c"


def render_icon(iconset: Path):
    """Render the 🎤 emoji into all required iconset PNG sizes via AppKit."""
    import AppKit

    iconset.mkdir(parents=True, exist_ok=True)
    for size in (16, 32, 64, 128, 256, 512, 1024):
        img = AppKit.NSImage.alloc().initWithSize_((size, size))
        img.lockFocus()
        attrs = {
            AppKit.NSFontAttributeName: AppKit.NSFont.systemFontOfSize_(size * 0.78)
        }
        text = AppKit.NSString.stringWithString_("🎤")
        bounds = text.sizeWithAttributes_(attrs)
        text.drawAtPoint_withAttributes_(
            ((size - bounds.width) / 2, (size - bounds.height) / 2), attrs
        )
        img.unlockFocus()
        tiff = img.TIFFRepresentation()
        rep = AppKit.NSBitmapImageRep.imageRepWithData_(tiff)
        png = rep.representationUsingType_properties_(AppKit.NSBitmapImageFileTypePNG, {})
        for name in {
            16: ["icon_16x16.png"],
            32: ["icon_32x32.png", "icon_16x16@2x.png"],
            64: ["icon_32x32@2x.png"],
            128: ["icon_128x128.png"],
            256: ["icon_256x256.png", "icon_128x128@2x.png"],
            512: ["icon_512x512.png", "icon_256x256@2x.png"],
            1024: ["icon_512x512@2x.png"],
        }[size]:
            png.writeToFile_atomically_(str(iconset / name), True)


def main():
    if DIST.parent.exists():
        shutil.rmtree(DIST.parent)
    macos = DIST / "Contents" / "MacOS"
    resources = DIST / "Contents" / "Resources"
    macos.mkdir(parents=True)
    resources.mkdir(parents=True)

    (DIST / "Contents" / "Info.plist").write_bytes(plistlib.dumps(INFO_PLIST))
    subprocess.run(
        [
            "clang",
            "-O2",
            f'-DCHILD_PATH="{PROJECT}/.venv/bin/local-dictation"',
            "-o",
            str(macos / "local-dictation"),
            str(LAUNCHER_SRC),
        ],
        check=True,
    )

    iconset = DIST.parent / "AppIcon.iconset"
    render_icon(iconset)
    subprocess.run(
        ["iconutil", "-c", "icns", str(iconset), "-o", str(resources / "AppIcon.icns")],
        check=True,
    )
    shutil.rmtree(iconset)

    subprocess.run(["codesign", "--force", "--deep", "-s", "-", str(DIST)], check=True)

    if INSTALL.exists():
        shutil.rmtree(INSTALL)
    shutil.copytree(DIST, INSTALL)
    subprocess.run(["codesign", "--verify", str(INSTALL)], check=True)
    print(f"Installed: {INSTALL}")


if __name__ == "__main__":
    main()
