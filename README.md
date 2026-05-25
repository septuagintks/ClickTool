# Click Tool (Minified)

An ultra-lightweight, **zero-dependency** Windows mouse auto-clicker. Uses direct Windows API calls for maximum portability and a tiny footprint.

## Quick Start

1. **Run**: Ensure Python is installed and run:
   ```bash
   python clicktoolm.py
   ```
2. **Portable**: Alternatively, run the single-file `ClickTool_m.pyz`.

## Key Features

- **Zero Dependencies**: Runs on any Windows system with Python; no `pip install` required.
- **Lightweight**: Optimized for background execution and minimal resource usage.
- **Screen & Window Mode**: Supports global coordinates (SendInput) and background client-area clicks (PostMessage).
- **Drag & Drop Targeting**: Hold and drag the crosshair icon onto any window to target it instantly.
- **Visual Setup**: Draggable numbered dots for easy positioning.
- **Self-Healing**: Automatically re-finds target windows by title if they are closed and reopened.
- **Robustness**: Automatic validation of action types with error logging to prevent silent script failure.
- **Automation**: Headless mode for Task Scheduler (`--auto --silent`).

## Usage

1. **Add Items**: Use the "Add" buttons to insert Click, Wheel, or Wait actions.
2. **Targeting**: In Window Mode, use "Add Window" and drag the crosshair to the target app.
3. **Position**: Drag the dots to your desired locations.
4. **Configure**: Set click buttons, scroll values, and individual delays in the list.
5. **Run**: Click **Start** or press **F8**. Press **Esc** to stop.

## Important Notes

- **Client-Area Only**: In Window Mode, dots are limited to the app's client area (no title-bar buttons).
- **Privileges**: Run as Administrator if your target application is also running with high privileges.
- **Compatibility**: Screen Mode uses hardware-level simulation for better compatibility with sensitive apps.
- **Automation**: Logs are rotated automatically and stored in `%LOCALAPPDATA%\ClickTool\logs\`.
- **Keyboard Hook**: Recording a Key action temporarily blocks system hotkeys. If it crashes during capture, restart your PC to restore normal behavior.
