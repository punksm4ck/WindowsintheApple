#!/usr/bin/env bash

mkdir -p ~/Scripts/AWindowInTheApple
cp AWindowInTheApple.py ~/Scripts/AWindowInTheApple/AWindowInTheApple.py
chmod +x ~/Scripts/AWindowInTheApple/AWindowInTheApple.py

PLIST_PATH="$HOME/Library/LaunchAgents/com.punks.awindow.plist"
PY_PATH=$(which python3)

cat << PLST > "$PLIST_PATH"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.punks.awindow</string>
    <key>ProcessType</key>
    <string>Interactive</string>
    <key>Nice</key>
    <integer>-20</integer>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/zsh</string>
        <string>-c</string>
        <string>PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin $PY_PATH ~/Scripts/AWindowInTheApple/AWindowInTheApple.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/dev/null</string>
    <key>StandardErrorPath</key>
    <string>/dev/null</string>
</dict>
</plist>
PLST

launchctl unload "$PLIST_PATH" 2>/dev/null
launchctl load "$PLIST_PATH"
