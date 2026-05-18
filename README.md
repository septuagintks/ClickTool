# Click Tool (Minified)

A lightweight, zero-dependency Windows mouse auto-clicker with visual draggable targets. This version uses direct Windows API calls via `ctypes` to ensure maximum portability without external libraries.

## Run

1.  Ensure you have Python installed.
2.  Start the app:

    ```bash
    python clicktoolm.py
    ```

## Features

### 1. Screen Mode
- **Global Coordinates**: Set click points anywhere on the screen.
- **Draggable Targets**: Visually position numbered dots.
- **Hardware Simulation**: Uses `SendInput` for compatibility with games and sensitive apps.

### 2. Window Mode
- **Target Windows**: Select specific windows to click within.
- **Drag & Drop Targeting**: Hold and drag the crosshair icon onto any window to target it instantly (Spy++ style).
- **Background Client Clicking**: Uses `PostMessage` and child-window detection for client-area clicks even when the window is not foregrounded.
- **Client-Only Dots**: Window dots are limited to the client area. Title bar buttons are intentionally not supported.
- **Smart Constraints**: Dots are locked within the client area and follow the window as it moves or resizes.
- **Self-Healing Windows**: If a targeted window is closed and reopened, the tool automatically re-resolves it by title match.
- **Cross-Window Sequencing**: Create sequences across multiple different windows.

### UI & UX Improvements
- **Settings Tab**: Window-mode behavior is separated from click sequence editing.
- **Compact Controls**: Run controls share one bottom bar to leave more room for click lists.
- **Optimized Dialogs**: Window selection dialogs use a tighter layout.
- **Bidirectional Selection**: Clicking a dot on the screen automatically selects its corresponding entry in the list.
- **Dot Hover Effects**: Dots visually highlight when the cursor hovers over them.

### General Features
- **Loop Toggle**: Choose between continuous looping or a single execution of your click sequence.
- **Script Management**: Export your entire setup (intervals, screen points, window targets, loop state) to a JSON file and import it later.
- **Auto-run Setup**: Save the current setup for `--auto --silent`.
- **Auto-refreshing Window List**: The "Add Window" dialog automatically updates the list of available windows.
- **Custom Delays**: Set unique wait times for each individual click point.
- **Custom Hotkeys**: Configure Start/Stop keyboard shortcuts via the Settings tab (supports symbol keys like `Ctrl+.`).
- **Global Hotkey Interception**: Start and stop sequences from any window without needing to focus ClickTool.
- **DPI Awareness**: Accurate positioning on high-resolution displays.
- **Log Rotation**: Auto-run logs are automatically rotated when they exceed 1 MB.

## Usage

1. **Choose Mode**: Use the tabs at the top to switch between **Screen Mode**, **Window Mode**, and **Settings**.
2. **Add Targets**:
   - In **Screen Mode**, click "Add Dot".
   - In **Window Mode**, click "Add Window" to pick a target. Once added, click "Add Dot".
3. **Position Dots**: Drag the numbered dots to your desired locations.
4. **Configure Sequence**: Adjust the order using Up/Down buttons and set custom post-click delays.
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

