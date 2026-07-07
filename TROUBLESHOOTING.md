# Surgical Troubleshooting

### Buttons aren't appearing?
1. **Permissions:** Ensure Python has Accessibility access.
2. **Restart Daemon:** `launchctl unload ~/Library/LaunchAgents/com.punks.awindow.plist && launchctl load ~/Library/LaunchAgents/com.punks.awindow.plist`

### High CPU usage?
The engine is throttled to 4ms (250Hz). If CPU spikes, check if another window manager (Magnet, Rectangle) is fighting for the Quartz event tap.

### Logs
Check standard error output:
`tail -f /tmp/window_apple_err.log` (if enabled in your local plist).
