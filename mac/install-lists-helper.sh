#!/bin/bash
# Build and install "Doorpost Lists" on the Mac (the Mac that stays on), and run it every 30 seconds.
# Rebuilding changes the app's signature, so macOS asks for Reminders permission again: only rebuild when main.swift changes.
#
# Settings (environment, all optional):
#   FRAME_URL        the frame server on your home network (default http://doorpost.local:8090)
#   HELPER_ID        the app's bundle id and the LaunchAgent label (default org.doorpost.frame-lists)
#   HELPER_NAME      the app's name (default "Doorpost Lists")
#   TOKEN_SERVICE    the Keychain item that holds the upload key, account "frame" (default "Doorpost upload token")
#   HELPER_LOG       the log file (default ~/Library/Logs/doorpost-lists.log)
# A private copy can keep the names it already uses, so an existing install is replaced, not doubled.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ID="${HELPER_ID:-org.doorpost.frame-lists}"
NAME="${HELPER_NAME:-Doorpost Lists}"
SERVICE="${TOKEN_SERVICE:-Doorpost upload token}"
APP="$HOME/Applications/$NAME.app"
PLIST="$HOME/Library/LaunchAgents/$ID.plist"
LOG="${HELPER_LOG:-$HOME/Library/Logs/doorpost-lists.log}"
mkdir -p "$APP/Contents/MacOS" "$HOME/Library/LaunchAgents"
swiftc -O "$HERE/lists-helper/main.swift" -o "$APP/Contents/MacOS/frame-lists"
cp "$HERE/lists-helper/Info.plist" "$APP/Contents/Info.plist"
plutil -replace CFBundleIdentifier -string "$ID" "$APP/Contents/Info.plist"
plutil -replace CFBundleName -string "$NAME" "$APP/Contents/Info.plist"
plutil -replace CFBundleDisplayName -string "$NAME" "$APP/Contents/Info.plist"
codesign --force --sign - --identifier "$ID" "$APP"
cat > "$PLIST" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$ID</string>
  <key>ProgramArguments</key><array><string>$APP/Contents/MacOS/frame-lists</string></array>
  <key>EnvironmentVariables</key><dict>
    <key>FRAME_URL</key><string>${FRAME_URL:-http://doorpost.local:8090}</string>
    <key>FRAME_TOKEN_SERVICE</key><string>$SERVICE</string>
  </dict>
  <key>StartInterval</key><integer>30</integer>
  <key>RunAtLoad</key><true/>
  <key>ProcessType</key><string>Background</string>
  <key>StandardErrorPath</key><string>$LOG</string>
</dict></plist>
PL
launchctl bootout "gui/$(id -u)/$ID" 2>/dev/null || true
# First run through Finder's way of opening apps, so macOS asks for Reminders permission for this app.
open -g "$APP" || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "Installed. If macOS asks, allow $NAME to use Reminders. Log: $LOG"
