#!/bin/zsh
set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo ""
echo "=================================================="
echo "  Local Dictation — Installer"
echo "=================================================="
echo ""
echo "This sets up Local Dictation on this Mac. It will:"
echo "  1. Check your Mac is compatible (Apple Silicon)"
echo "  2. Install 'uv' (a small Python tool manager), if needed"
echo "  3. Check for Ollama (used to clean up your speech), if needed"
echo "  4. Download everything Local Dictation needs to run"
echo "  5. Build and install the app into your Applications folder"
echo "  6. Ask macOS for Microphone and Accessibility permission"
echo ""
read "?Press Enter to begin, or close this window to cancel... "

# 1. Apple Silicon check
if [[ "$(uname -m)" != "arm64" ]]; then
  echo ""
  echo "Sorry — Local Dictation only runs on Apple Silicon Macs (M1/M2/M3/M4)."
  echo "This Mac reports '$(uname -m)', so it isn't supported."
  read "?Press Enter to close this window... "
  exit 1
fi
echo "Apple Silicon Mac detected"

# 2. uv (installs and runs Local Dictation's Python environment)
if ! command -v uv >/dev/null 2>&1; then
  echo ""
  echo "Installing 'uv'..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi
if ! command -v uv >/dev/null 2>&1; then
  echo ""
  echo "uv was installed, but this window can't see it yet."
  echo "Close this window, open a new one, and double-click this installer again."
  read "?Press Enter to close this window... "
  exit 1
fi
echo "uv is installed"

# 3. Ollama — optional local AI that cleans up "um"s and grammar
OLLAMA_MODEL="qwen3:4b-instruct"
if ! command -v ollama >/dev/null 2>&1; then
  echo ""
  echo "Local Dictation can use Ollama (a free, local AI) to clean up 'ums' and"
  echo "grammar in what you say. It's optional — Local Dictation still works"
  echo "without it, just with raw, unedited speech-to-text."
  echo ""
  echo "Opening the Ollama download page in your browser..."
  open "https://ollama.com/download" || true
  echo ""
  read "?If you want it, install Ollama now, then press Enter to continue (or just press Enter to skip)... "
fi

if command -v ollama >/dev/null 2>&1; then
  echo ""
  echo "Ollama found — starting it and downloading its speech-cleanup model."
  echo "(one-time download, a few GB — this may take several minutes)"
  open -a Ollama >/dev/null 2>&1 || true
  sleep 3
  ollama pull "$OLLAMA_MODEL" || echo "Couldn't download the model right now. You can retry later, or turn off 'AI Cleanup' in the app's menu."
else
  echo "Skipping Ollama. You can turn off 'AI Cleanup' in the app's menu so it"
  echo "still works fine without it."
fi

# 4. Download Local Dictation's own components
echo ""
echo "Setting up Local Dictation (downloading its speech-recognition models)..."
uv sync

# 5. Build and install the app bundle
echo ""
echo "Building the app..."
if ! uv run python scripts/build_app.py; then
  echo ""
  echo "The build failed. If macOS just showed a popup about installing"
  echo "'Command Line Developer Tools', click Install, wait for it to finish"
  echo "downloading, then run this installer again."
  read "?Press Enter to close this window... "
  exit 1
fi
echo ""
echo "Installed to /Applications/Local Dictation.app"

# 6. Permissions
echo ""
echo "Launching Local Dictation and opening System Settings so you can grant"
echo "two permissions..."
open "/Applications/Local Dictation.app"
sleep 2
open "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone" || true
sleep 1
open "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility" || true

echo ""
echo "=================================================="
echo "  Almost done!"
echo "=================================================="
echo ""
echo "In System Settings, turn ON \"Local Dictation\" under both:"
echo "  - Microphone"
echo "  - Accessibility"
echo ""
echo "Then fully quit Local Dictation (right-click its menu-bar icon > Quit)"
echo "and reopen it from your Applications folder."
echo ""
echo "To use it: hold the Right Option key, speak, then let go."
echo ""
read "?Press Enter to close this window... "
