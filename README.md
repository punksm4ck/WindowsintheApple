AWindowInTheApple

A commercial-grade macOS utility that retrofits native windows with high-performance, Windows-style control buttons. 

Technical Breakthroughs
* 250Hz Hardware Tracking: Latency-free window dragging that maintains a super-glued feel.
* Ray-Cast Occlusion Matrix: Mathematically calculates window Z-depth to prevent UI bleed-through.
* Interactive Daemon: Custom launchd integration with high-priority scheduling (Nice -20) to ensure availability immediately upon login.
* Accessibility Sandbox Bypass: Uses synthetic event injection to control hostile applications (Electron, PWAs) that traditionally ignore macOS window commands.

Installation
1. Grant Accessibility permissions to your Terminal in System Settings.
2. Load the daemon:
   launchctl load ~/Library/LaunchAgents/com.punks.awindow.plist

Key Aliases
* win-stop: Temporarily pause the UI enhancements.
* win-start: Re-arm the engine.
