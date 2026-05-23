# Click Tool (Minified)

A lightweight, zero-dependency Windows mouse auto-clicker with visual draggable targets. This version uses direct Windows API calls via `ctypes` to ensure maximum portability without external libraries.

## Quick Start

1. Ensure you have Python installed
2. Run the app:
   ```bash
   python clicktoolm.py
   ```

## Task Scheduler Automation

Use the GUI **Auto Config** button to save the startup configuration. The app stores it at:

```
%LOCALAPPDATA%\ClickTool\auto_config.json
```

Then configure Windows Task Scheduler to start the packaged executable with:

```bash
ClickTool.exe --auto --silent
```

For script testing, use:

```bash
python clicktoolm.py --auto --silent
```

Pass `--config <path>` to override the default config location.

Automation behavior:
- Reads the saved auto config
- Runs without opening the Tkinter UI
- Allows only one Click Tool instance at a time
- Waits for configured target windows before clicking in Window Mode
- Self-heals window targets by re-resolving by title (exact match, then case-insensitive substring) if a HWND becomes invalid mid-run
- Exits automatically when the saved run finishes
- If **Loop** is enabled, automation stops at the first reached safety limit: default `60` seconds or `3` completed rounds
- Auto-run logs are written next to the config and rotated when they exceed 1 MB

## Features

### Screen Mode
- **Global Coordinates**: Set click points anywhere on the screen
- **Mouse Actions**: Left, right, middle, side-button clicks, and wheel scroll actions
- **Keyboard Actions**: Record and replay keyboard input with modifier keys (Ctrl, Alt, Shift, Win). Uses scancode-based injection for layout-independent playback
- **Draggable Targets**: Visually position numbered dots
- **Hardware Simulation**: Uses `SendInput` for compatibility with games and sensitive apps

### Window Mode
- **Target Windows**: Select specific windows to click within
- **Drag & Drop Targeting**: Hold and drag the crosshair icon onto any window to target it instantly (Spy++ style)
- **Background Client Actions**: Uses `PostMessage` for client-area clicks, wheel actions, and keyboard input even when the window is not foregrounded
- **Client-Only Dots**: Window dots are limited to the client area. Title bar buttons are intentionally not supported (this is the only intentional functional difference from the main branch — the minified build does not expose a Pure Background toggle because it always behaves as if it were on, to stay dependency-free)
- **Smart Constraints**: Dots are locked within the client area and follow the window as it moves or resizes
- **Self-Healing Windows**: If a targeted window is closed and reopened, the tool automatically re-resolves it by title match
- **Cross-Window Sequencing**: Create sequences across multiple different windows

### General Features
- **Loop Toggle**: Choose between continuous looping or a single execution of your click sequence
- **Script Management**: Export your entire setup to a JSON file and import it later
- **Auto-run Setup**: Save the current setup for `--auto --silent`
- **Custom Delays**: Set unique wait times for each individual click point
- **Action Editing**: Click actions can choose `left`, `right`, `middle`, `x1`, or `x2`; wheel actions use positive deltas for upward scrolling and negative deltas for downward scrolling; keyboard actions support modifier combinations; standalone Wait items insert pauses between actions
- **Defaults & Shortcuts**: The Settings tab can change the default run interval, default wait-item duration, and app shortcuts for Start, Stop, Add Window, Add Dot, Add Wheel, Add Key, Add Wait, and Clear
- **Global Hotkey Interception**: Start, Stop, and add/clear actions can be triggered from any window without focusing ClickTool
- **Hotkey Scope Toggle**: Settings → Hotkey Scope → "Enable global hotkeys" turns global interception on (default) or off. Disable it before typing into apps that share the same shortcut letters to avoid conflicts
- **DPI Awareness**: Accurate positioning on high-resolution displays
- **Log Rotation**: Auto-run logs are automatically rotated when they exceed 1 MB

## Usage

1. **Choose Mode**: Use the tabs at the top to switch between **Screen Mode**, **Window Mode**, and **Settings**
2. **Add Targets**:
   - In **Screen Mode**, use the **Add** group to insert a Dot, Wheel, Key, or Wait item
   - Click "Add Key" to record a keyboard action. Focus the input box and press your desired key combination (e.g., `Ctrl+C`, `Alt+Tab`, `Win+D`). The action is saved when all keys are released
   - In **Window Mode**, click "Add Window" to pick a target. Once added, use the **Add** group to insert a Dot, Wheel, Key, or Wait item
3. **Position Dots**: Drag the numbered dots to your desired locations
4. **Configure Sequence**: Adjust the order using Up/Down buttons, choose the click button for click actions, edit wheel deltas, re-record key combinations, and set per-step custom delays
5. **Set Execution**: Toggle the **Loop** checkbox to enable or disable continuous clicking
6. **Save/Load**: Use **Export** to save your configuration and **Import** to load it later
7. **Auto-run Setup**: Use **Auto Config** to write the startup config for `--auto --silent`
8. **Configure Hotkeys**: Go to **Settings** tab to customize Start/Stop shortcuts
9. **Run**: Click **Start** or press your configured hotkey (default: **F8**). Press **ESC** (or your configured stop key) to stop

## Dependencies

**None** — This is the lightweight version using direct Windows API calls.

Standard libraries used: `tkinter`, `json`, `threading`, `ctypes`, `time`, `argparse`, `os`, `sys`, `datetime`.

## Build

Two release formats are produced from this branch:

### `.pyz` (recommended for minified)

Build a Python zipapp — single file, ~400 KB, requires Python on the target machine but no third-party deps:

```bash
python -m zipapp <stage_dir> -o ClickTool_m.pyz -p "/usr/bin/env python"
```

Where `<stage_dir>` contains `clicktoolm.py`, the `clicktool_min/` package, and a `__main__.py` with:

```python
from clicktoolm import main
import sys
sys.exit(main())
```

Run with `python ClickTool_m.pyz`.

### Standalone `.exe`

You can also compile to a single executable using PyInstaller:

```bash
pip install pyinstaller
python -m PyInstaller --onefile --windowed --name=ClickTool_m --collect-submodules=clicktool_min clicktoolm.py
```

This is mostly redundant with the main branch's `ClickTool.exe`. The minified branch is intended to ship as `.pyz` so users get the zero-dependency benefit.

## Caveats & Warnings

### Elevated Process Limitations

ClickTool **cannot inject input into processes running with higher privileges** than itself. This includes:
- Applications launched as Administrator (elevated/UAC)
- UAC consent dialogs and system security prompts
- Windows Store apps (UWP) with AppContainer isolation
- System services and protected processes

**Workaround**: Run ClickTool as Administrator to match the target's privilege level, or use Screen Mode which may have better compatibility in some scenarios. Note that even with elevated privileges, some system-protected windows remain inaccessible.

### Background Clicking

Window Mode uses `PostMessage` for background clicks. This build is **client-area only** and does not support title-bar or border clicks in background mode. Some applications may ignore background messages entirely.

### Keyboard Capture

When recording a Key action, ClickTool installs a low-level keyboard hook. This **temporarily suppresses all system hotkeys** (like `Win+R` or `Alt+Tab`) to ensure the combination is captured correctly. Normal system behavior restores automatically once you release all keys or click away from the input box. **If the application crashes during capture, restart your computer to restore normal keyboard behavior.**

### Input Injection

Some security-sensitive applications or games may block programmatic input injection. Screen Mode uses `SendInput` (hardware simulation), which offers the best compatibility.

### Multi-Monitor

Screen Mode uses `SendInput` with `MOUSEEVENTF_VIRTUALDESK` and the virtual desktop bounds, so dots placed on a secondary display click the correct spot. Window Mode is HWND-relative and unaffected by monitor layout.

### Log Rotation

Automatic logs are stored in `%LOCALAPPDATA%\ClickTool\logs\` and are automatically rotated (using atomic replacement with file locking) once they exceed 1 MB to prevent excessive disk usage. Multi-process log writes are protected by a dedicated lock file to prevent interleaving.

### Error Reporting

Unexpected errors are captured with full stack traces in the application log to aid in troubleshooting.
