#!/bin/zsh
# Double-click to start Local Dictation (runs in Terminal so it inherits
# Terminal's Microphone and Accessibility permissions).
cd "$(dirname "$0")"
echo "Starting Local Dictation — look for the mic icon in the menu bar."
echo "Keep this window open; dictation activity is logged here. Ctrl+C to quit."
exec .venv/bin/local-dictation
