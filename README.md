# WindowsintheApple v1.0.0

A doctorate-level macOS utility that retrofits native window management with high-performance, Windows-style controls and precision key remapping.

## Core Architecture
* **250Hz Hardware Tracking:** Latency-free button anchoring that maintains a "super-glued" feel to the window chrome.
* **Ray-Cast Occlusion Matrix:** Real-time Z-depth calculation to prevent UI bleed-through and ghost-clicks.
* **Synthetic Event Injection:** Restores CTRL-based shortcuts (C, V, X, Z, A, F) while preserving the native macOS CMD+Tab switcher.
* **Interactive Daemon:** Custom `launchd` integration with high-priority scheduling (`Nice -20`).

## One-Line Deployment
Run this command in Terminal to install or update instantly:
`curl -sL https://raw.githubusercontent.com/punksm4ck/WindowsintheApple/main/install.sh | bash`

## Prerequisites
* **Python 3.9+**
* **PyObjC & Tkinter:** `pip3 install pyobjc-framework-Quartz pyobjc-framework-AppKit`
* **Accessibility Permissions:** You must grant your Terminal (or the Python binary) Accessibility access in `System Settings > Privacy & Security > Accessibility`.

## Identity & Privacy
This project is maintained by **punksm4ck**. All identifiers have been scrubbed for professional anonymity.
