# Click Tool

A flexible Windows mouse auto-clicker with visual draggable targets. Supports both screen-wide and window-specific clicking modes.

## Run

1. Activate the virtual environment:

   ```bash
   .venv\Scripts\activate
   ```

2. Install dependencies (requires `pywin32`):

   ```bash
   pip install -r requirements.txt
   ```

3. Start the app:

   ```bash
   python clicktool.py
   ```

### Task Scheduler Automation

Use the GUI **Auto Config** button to save the startup configuration first. The app stores it at:

```text
%LOCALAPPDATA%\ClickTool\auto_config.json
```

Then configure Windows Task Scheduler to start the packaged executable with:

```bash
ClickTool.exe --auto --silent
```

For script testing, the same automation path can be started with:

```bash
python clicktool.py --auto --silent
```

### Multi-Monitor

Screen Mode uses real screen coordinates via `SetCursorPos`, so dots placed on a secondary display click the correct spot. Window Mode is HWND-relative and unaffected by monitor layout.

### Console window

Launching with `python clicktool.py` (no `--auto`) automatically re-launches under `pythonw.exe` so the console window disappears. `--auto` keeps the console for stdout; `--auto --silent` calls `FreeConsole()` for Task Scheduler.

Automation behavior:
- Reads the saved auto config.
- Runs without opening the Tkinter UI.
- Allows only one Click Tool instance at a time.
- Waits for configured target windows before clicking in Window Mode.
- Exits automatically when the saved run finishes.
- If the saved config has **Loop** enabled, automation stops at the first reached safety limit: default `60` seconds or `3` completed rounds.

## Caveats & Warnings

- **Elevated Process Limitations**: ClickTool **cannot inject input into processes running with higher privileges** than itself. This includes:
  - Applications launched as Administrator (elevated/UAC)
  - UAC consent dialogs and system security prompts
  - Windows Store apps (UWP) with AppContainer isolation
  - System services and protected processes
  
  **Workaround**: Run ClickTool as Administrator to match the target's privilege level, or use Screen Mode which may have better compatibility in some scenarios. Note that even with elevated privileges, some system-protected windows remain inaccessible.

- **Background Clicking**: Window Mode uses `PostMessage` for background clicks. While effective for many standard Windows apps, some applications (especially those using custom UI frameworks, hardware acceleration, or anti-cheat) may ignore background messages. If background clicking fails, try using **Screen Mode**.

- **Keyboard Capture**: When recording a Key action, ClickTool installs a low-level keyboard hook. This **temporarily suppresses all system hotkeys** (like `Win+R` or `Alt+Tab`) to ensure the combination is captured correctly. Normal system behavior restores automatically once you release all keys or click away from the input box. **If the application crashes during capture, restart your computer to restore normal keyboard behavior.**

- **Input Injection**: Some security-sensitive applications or games may block programmatic input injection. Screen Mode uses `SendInput` (hardware simulation), which offers the best compatibility.

- **Multi-Instance Logging**: If running multiple ClickTool instances simultaneously (e.g., via Task Scheduler), log file writes may occasionally interleave. For production automation, use a single instance or separate log directories.

- **Log Rotation**: Automatic logs are stored in `%LOCALAPPDATA%\ClickTool\logs\` and are automatically rotated (using atomic replacement) once they exceed 1 MB to prevent excessive disk usage.

- **Error Reporting**: Unexpected errors are now captured with full stack traces in the application log to aid in troubleshooting.

## Features

### 1. Screen Mode
- **Global Coordinates**: Set mouse action points anywhere on the screen.
- **Mouse Actions**: Supports left, right, middle, side-button clicks, and wheel scroll actions.
- **Keyboard Actions**: Record and replay keyboard input with modifier keys (Ctrl, Alt, Shift, Win). Uses scancode-based injection for layout-independent playback.
- **Draggable Targets**: Visually position numbered dots.

### 2. Window Mode
- **Target Windows**: Select specific windows to click within.
- **Background Client Actions**: Uses `PostMessage` for client-area clicks, wheel actions, and keyboard input even when the window is not foregrounded.
- **Title Bar Support**: When pure background mode is off, non-client clicks such as title-bar buttons fall back to real mouse input for better compatibility.
- **Pure Background Mode**: The Settings tab can enable pure background window clicking. In this mode, window dots are limited to the client area and title-bar clicks are not supported.
- **Smart Constraints**: Dots are locked within the active window-mode range and follow the window as it moves or resizes.
- **Cross-Window Sequencing**: Create sequences across multiple different windows.

### UI & UX Improvements
- **Settings Tab**: Window-mode behavior is configured separately from click sequences. Dots from the most recently used Screen / Window tab stay visible while editing settings, so coordinate adjustments and shortcut tweaks have live visual feedback.
- **Compact Controls**: Run, import/export, loop, and interval controls share one bottom bar to leave more room for click lists. Action buttons are grouped by add/edit tasks instead of a single long row.
- **Optimized Dialogs**: Window selection and auto configuration dialogs use more compact layouts.
- **Bidirectional Selection**: Clicking a dot on the screen automatically selects its corresponding entry in the list.
- **Smart Hotkey Placement**: Creating action points (Dot or Wheel) via global hotkeys automatically places them exactly at the current position of the mouse cursor. In Window Mode, if the cursor is within the targeted window bounds, it automatically calculates the coordinates relative to that window. (Directly clicking the GUI "Add" buttons still defaults to the screen/window center).
### General Features
- **Loop Toggle**: Choose between continuous looping or a single execution of your click sequence.
- **Script Management**: Export your entire setup (intervals, screen points, window targets, loop state) to a JSON file and import it later.
- **Auto Startup Config**: Import a script or save the current setup as the Task Scheduler auto-run config, including loop timeout and max-round limits.
- **Auto-refreshing Window List**: The "Add Window" dialog automatically updates the list of available windows.
- **Custom Delays**: Set unique wait times for each individual click point.
- **Action Editing**: Click actions can choose `left`, `right`, `middle`, `x1`, or `x2`; wheel actions use positive deltas for upward scrolling and negative deltas for downward scrolling; keyboard actions support modifier combinations (Ctrl, Alt, Shift, Win).
- **Defaults & Shortcuts**: The Settings tab can change the run interval, default wait-item duration, and app shortcuts for Start, Stop, Add Window, Add Dot, Add Wheel, Add Key, Add Wait, and Clear.
- **Global Hotkey Scope Toggle**: Settings → Hotkey Scope → "Enable global hotkeys" controls whether shortcuts trigger system-wide (default) or only when ClickTool has focus. Disable it to avoid conflicts while typing in other apps.
- **DPI Awareness**: Accurate positioning on high-resolution displays.
- **Emergency Stop**: Press **Esc** at any time to stop the clicking loop.

## Usage

1. **Choose Mode**: Use the tabs at the top to switch between **Screen Mode**, **Window Mode**, and **Settings**.
2. **Optional Window Setting**: In **Settings**, enable **Pure background clicking** if window-mode clicks must never use real mouse input. This limits window dots to the target window's client area.
3. **Optional Defaults**: In **Settings**, adjust the default interval, default wait duration, and shortcut keys. Shortcut examples include `Ctrl+D`, `Ctrl+Shift+W`, and `Esc`.
4. **Add Targets**:
   - In **Screen Mode**, click "Add Dot".
   - Click "Add Wheel" to create a scroll action at a draggable point.
   - Click "Add Key" to record a keyboard action. Focus the input box and press your desired key combination (e.g., `Ctrl+C`, `Alt+Tab`, `Win+D`). The action is saved when all keys are released.
   - In **Window Mode**, click "Add Window" to pick a target (the list refreshes automatically). Once added, the window is automatically selected so you can immediately click "Add Dot", "Add Wheel", or "Add Key".
5. **Position Dots**: Drag the numbered dots to your desired locations.
6. **Configure Sequence**: Adjust the order using Up/Down buttons, choose the click button for click actions, edit wheel deltas, re-record key combinations, and set waits.
7. **Set Execution**: Toggle the **Loop** checkbox to enable or disable continuous clicking.
8. **Save/Load**: Use **Export** to save your configuration and **Import** to load a previously saved setup.
9. **Auto-run Setup**: Use **Auto Config** to import a script or save the current setup for `--auto --silent`. For looped auto configs, set the timeout and max-round safety limits.
10. **Run**: Click **Start**. Press **Esc** to stop.

## Build Executable

You can compile this tool into a standalone executable using PyInstaller:

```bash
pip install pyinstaller
python -m PyInstaller --onefile --windowed --name=ClickTool --collect-submodules=clicktool clicktool.py
```

This produces a single `dist/ClickTool.exe` (~12.8 MB) that runs without Python or any dependencies installed.

*Note: Requires `pywin32` to be installed in the build environment.*

## Release

| Artifact | Description |
|----------|-------------|
| `ClickTool.exe` | Main branch, single-file executable (Nuitka onefile) |
| `ClickTool_m.pyz` | Minified branch, Python zipapp (requires Python, zero third-party deps) |

Run the pyz with:

```bash
python ClickTool_m.pyz
```
