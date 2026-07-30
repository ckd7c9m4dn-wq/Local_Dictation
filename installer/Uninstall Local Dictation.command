#!/bin/zsh

echo "Uninstalling Local Dictation..."

osascript -e 'quit app "Local Dictation"' >/dev/null 2>&1
pkill -f "local-dictation" >/dev/null 2>&1
launchctl bootout "gui/$(id -u)/com.mhardy.local-dictation" >/dev/null 2>&1
rm -f ~/Library/LaunchAgents/com.mhardy.local-dictation.plist
rm -rf "/Applications/Local Dictation.app"

echo ""
echo "Removed the app and its login item."
echo ""
echo "Your settings and dictation history are still kept at:"
echo "  ~/.config/local_dictation"
echo "Delete that folder too if you want to remove everything."
echo ""
read "?Press Enter to close this window... "
