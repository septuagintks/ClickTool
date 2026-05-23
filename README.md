# Click Tool

A flexible Windows mouse auto-clicker with visual draggable targets. Supports both screen-wide and window-specific clicking modes.

## Quick Start

1. **Download**: Grab `ClickTool.exe` from the latest release.
2. **Run**: Double-click to start. No installation required.
3. **From Source**:
   ```bash
   pip install -r requirements.txt
   python clicktool.py
   ```

## Key Features

- **Screen Mode**: Position numbered dots anywhere on the screen.
- **Window Mode**: Click inside specific windows, even in the background. Supports title-bar buttons (standard mode) or client-area only (pure background mode).
- **Multiple Actions**: Left/Right/Middle/Side clicks, Wheel scrolls, and Keyboard combinations (Scancode-based for accuracy).
- **Visual Setup**: Drag and drop dots to set coordinates.
- **Smart Logic**: Automatic window self-healing (re-resolves by title), custom per-step delays, and loop safety limits.
- **Global Hotkeys**: Start/Stop (Default: **F8** / **Esc**) and capture coordinates from any window.

## Usage

1. **Add Targets**: Use "Add Dot/Wheel/Key" in Screen Mode or "Add Window" first in Window Mode.
2. **Position**: Drag the dots to your target locations.
3. **Configure**: Adjust click buttons, scroll deltas, or key combinations in the list.
4. **Run**: Click **Start** or press **F8**. Press **Esc** to stop.
5. **Automation**: Use **Auto Config** to save settings, then run via Task Scheduler: `ClickTool.exe --auto --silent`.

## Caveats & Tips

- **Privileges**: To click on an Administrator app, you must run ClickTool as Administrator.
- **Background Mode**: Some apps (games/HW accelerated) may ignore background messages; use **Screen Mode** instead.
- **Emergency Stop**: Press **Esc** to immediately stop any running sequence.
- **Keyboard Capture**: While recording a Key action, system hotkeys are temporarily suppressed. Normal behavior restores once you release all keys.
- **Logs**: Auto-run logs are saved in `%LOCALAPPDATA%\ClickTool\logs\`.
