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
- **Settings Tab**: Window-mode behavior is separated from click sequence editing.
- **Compact Controls**: Run controls share one bottom bar to leave more room for click lists. Action buttons are grouped by add/edit tasks.
- **Optimized Dialogs**: Window selection dialogs use a tighter layout.
- **Bidirectional Selection**: Clicking a dot on the screen automatically selects its corresponding entry in the list.
- **Dot Hover Effects**: Dots visually highlight when the cursor hovers over them. Wheel-action dots are styled in purple to distinguish them from click dots.

### General Features
- **Loop Toggle**: Choose between continuous looping or a single execution of your click sequence.
- **Script Management**: Export your entire setup (intervals, screen points, window targets, loop state, action types) to a JSON file and import it later.
- **Auto-run Setup**: Save the current setup for `--auto --silent`.
- **Auto-refreshing Window List**: The "Add Window" dialog automatically updates the list of available windows.
- **Custom Delays**: Set unique wait times for each individual click point.
- **Action Editing**: Click actions can choose `left`, `right`, `middle`, `x1`, or `x2`; wheel actions use positive deltas for upward scrolling and negative deltas for downward scrolling; standalone Wait items insert pauses between actions.
- **Custom Hotkeys**: Configure Start/Stop keyboard shortcuts via the Settings tab (supports symbol keys like `Ctrl+.`).
- **Global Hotkey Interception**: Start and stop sequences from any window without needing to focus ClickTool.
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

