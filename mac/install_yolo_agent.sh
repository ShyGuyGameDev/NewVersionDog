#!/bin/bash
# Install LaunchAgent so Mac YOLO starts at login and stays running.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST_SRC="$SCRIPT_DIR/com.spatialai.dogyolo.plist"
PLIST_DST="$HOME/Library/LaunchAgents/com.spatialai.dogyolo.plist"

mkdir -p "$HOME/Library/LaunchAgents"
cp "$PLIST_SRC" "$PLIST_DST"

# Unload if already loaded (ignore errors)
launchctl bootout "gui/$(id -u)/com.spatialai.dogyolo" 2>/dev/null || true
launchctl unload "$PLIST_DST" 2>/dev/null || true

launchctl bootstrap "gui/$(id -u)" "$PLIST_DST" 2>/dev/null \
  || launchctl load "$PLIST_DST"

echo "Installed LaunchAgent: $PLIST_DST"
echo "YOLO agent should now be running on port 8010."
echo "Check: curl -s http://127.0.0.1:8010/health"
echo "Logs:  /tmp/dog_yolo_agent.log  /tmp/dog_yolo_agent.err"
