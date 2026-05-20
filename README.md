# Click Tool (Minified)

A lightweight, zero-dependency Windows mouse auto-clicker with visual draggable targets. This version uses direct Windows API calls via `ctypes` to ensure maximum portability without external libraries.

## Run

1.  Ensure you have Python installed.
2.  Start the app:

    ```bash
    python clicktoolm.py
    ```

### Task Scheduler Automation

Use the GUI **Save Auto** button to save the startup configuration first. The app stores it at:

```text
%LOCALAPPDATA%\ClickTool\auto_config.json
```

Then configure Windows Task Scheduler to start the packaged executable with:

```bash
ClickTool.exe --auto --silent
```

For script testing, the same automation path can be started with:

```bash
python clicktoolm.py --auto --silent
```

Pass `--config <path>` to override the default config location.

Automation behavior:
- Reads the saved auto config.
- Runs without opening the Tkinter UI.
- Allows only one Click Tool instance at a time.
- Waits for configured target windows before clicking in Window Mode.
- Self-heals window targets by re-resolving by title (exact match, then case-insensitive substring) if a HWND becomes invalid mid-run.
- Exits automatically when the saved run finishes.
- If the saved config has **Loop** enabled, automation stops at the first reached safety limit: default `60` seconds or `3` completed rounds.
- Auto-run logs are written next to the config and rotated when they exceed 1 MB.

## Features

### 1. Screen Mode
- **Global Coordinates**: Set click points anywhere on the screen.
- **Mouse Actions**: Supports left, right, middle, side-button clicks, and wheel scroll actions.
- **Draggable Targets**: Visually position numbered dots.
- **Hardware Simulation**: Uses `SendInput` for compatibility with games and sensitive apps.

### 2. Window Mode
- **Target Windows**: Select specific windows to click within.
- **Drag & Drop Targeting**: Hold and drag the crosshair icon onto any window to target it instantly (Spy++ style).
- **Background Client Actions**: Uses `PostMessage` and child-window detection for client-area clicks and wheel actions even when the window is not foregrounded.
- **Client-Only Dots**: Window dots are limited to the client area. Title bar buttons are intentionally not supported (this is the only intentional functional difference from the main branch — the minified build does not expose a Pure Background toggle because it always behaves as if it were on, to stay dependency-free).
- **Smart Constraints**: Dots are locked within the client area and follow the window as it moves or resizes.
- **Self-Healing Windows**: If a targeted window is closed and reopened, the tool automatically re-resolves it by title match.
- **Cross-Window Sequencing**: Create sequences across multiple different windows.

### UI & UX Improvements
- **Settings Tab**: Window-mode notes, default Interval / Wait values, and shortcut customization are grouped here.
- **Compact Controls**: Run controls share one bottom bar to leave more room for click lists. Action buttons are grouped by add/edit tasks.
- **Optimized Dialogs**: Window selection dialogs use a tighter layout.
- **Bidirectional Selection**: Clicking a dot on the screen automatically selects its corresponding entry in the list.
- **Smart Hotkey Placement**: Creating action points (Dot or Wheel) via global hotkeys automatically places them exactly at the current position of the mouse cursor. In Window Mode, if the cursor is within the targeted window bounds, it automatically calculates the coordinates relative to that window. (Directly clicking the GUI "Add" buttons still defaults to the screen/window center.)
- **Dot Hover Effects**: Dots visually highlight when the cursor hovers over them. Wheel-action dots are styled in purple to distinguish them from click dots.

### General Features
- **Loop Toggle**: Choose between continuous looping or a single execution of your click sequence.
- **Script Management**: Export your entire setup (intervals, screen points, window targets, loop state, action types) to a JSON file and import it later.
- **Auto-run Setup**: Save the current setup for `--auto --silent`.
- **Auto-refreshing Window List**: The "Add Window" dialog automatically updates the list of available windows.
- **Custom Delays**: Set unique wait times for each individual click point.
- **Action Editing**: Click actions can choose `left`, `right`, `middle`, `x1`, or `x2`; wheel actions use positive deltas for upward scrolling and negative deltas for downward scrolling; standalone Wait items insert pauses between actions.
- **Defaults & Shortcuts**: The Settings tab can change the default run interval, default wait-item duration, and app shortcuts for Start, Stop, Add Window, Add Dot, Add Wheel, Add Wait, and Clear.
- **Global Hotkey Interception**: Start, Stop, and add/clear actions can be triggered from any window without focusing ClickTool.
- **DPI Awareness**: Accurate positioning on high-resolution displays.
- **Log Rotation**: Auto-run logs are automatically rotated when they exceed 1 MB.

## Usage

1. **Choose Mode**: Use the tabs at the top to switch between **Screen Mode**, **Window Mode**, and **Settings**.
2. **Add Targets**:
   - In **Screen Mode**, use the **Add** group to insert a Dot, Wheel, or Wait item.
   - In **Window Mode**, click "Add Window" to pick a target. Once added, use the **Add** group to insert a Dot, Wheel, or Wait item.
3. **Position Dots**: Drag the numbered dots to your desired locations.
4. **Configure Sequence**: Adjust the order using Up/Down buttons, choose the click button for click actions, edit wheel deltas, and set per-step custom delays.
5. **Set Execution**: Toggle the **Loop** checkbox to enable or disable continuous clicking.
6. **Save/Load**: Use **Export** to save your configuration and **Import** to load it later.
7. **Auto-run Setup**: Use **Save Auto** to write the startup config for `--auto --silent`.
8. **Configure Hotkeys**: Go to **Settings** tab to customize Start/Stop shortcuts.
9. **Run**: Click **Start** or press your configured hotkey (default: **F8**). Press **ESC** (or your configured stop key) to stop.

## Dependencies
- **None**: This is the lightweight version using direct Windows API calls.
- Standard libraries used: `tkinter`, `json`, `threading`, `ctypes`, `time`, `argparse`, `os`, `sys`, `datetime`.

## Build Executable

You can compile this tool into a standalone executable using `nuitka`:

```bash
nuitka --onefile --windows-console-mode=disable clicktoolm.py
```

