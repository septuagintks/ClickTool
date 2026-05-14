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
   python main.py
   ```

### Task Scheduler Automation

Use the GUI **Auto Config** button to save the startup configuration first. The app stores it at:

```text
%LOCALAPPDATA%\ClickTool\auto_config.json
```

Then configure Windows Task Scheduler to start the packaged executable with:

```bash
tool.exe --auto --silent
```

For script testing, the same automation path can be started with:

```bash
python main.py --auto --silent
```

Automation behavior:
- Reads the saved auto config.
- Runs without opening the Tkinter UI.
- Allows only one Click Tool instance at a time.
- Waits for configured target windows before clicking in Window Mode.
- Exits automatically when the saved run finishes.
- If the saved config has **Loop** enabled, automation stops at the first reached safety limit: default `60` seconds or `3` completed rounds.

## Features

### 1. Screen Mode
- **Global Coordinates**: Set click points anywhere on the screen.
- **Draggable Targets**: Visually position numbered dots.

### 2. Window Mode
- **Target Windows**: Select specific windows to click within.
- **Background Client Clicking**: Uses `PostMessage` and child-window detection for client-area clicks even when the window is not foregrounded.
- **Title Bar Support**: When pure background mode is off, non-client clicks such as title-bar buttons fall back to real mouse input for better compatibility.
- **Pure Background Mode**: The Settings tab can enable pure background window clicking. In this mode, window dots are limited to the client area and title-bar clicks are not supported.
- **Smart Constraints**: Dots are locked within the active window-mode range and follow the window as it moves or resizes.
- **Cross-Window Sequencing**: Create sequences across multiple different windows.

### UI & UX Improvements
- **Settings Tab**: Window-mode behavior is configured separately from click sequences.
- **Compact Controls**: Run, import/export, loop, and interval controls share one bottom bar to leave more room for click lists.
- **Optimized Dialogs**: Window selection and auto configuration dialogs use more compact layouts.
- **Bidirectional Selection**: Clicking a dot on the screen automatically selects its corresponding entry in the list.
### General Features
- **Loop Toggle**: Choose between continuous looping or a single execution of your click sequence.
- **Script Management**: Export your entire setup (intervals, screen points, window targets, loop state) to a JSON file and import it later.
- **Auto Startup Config**: Import a script or save the current setup as the Task Scheduler auto-run config, including loop timeout and max-round limits.
- **Auto-refreshing Window List**: The "Add Window" dialog automatically updates the list of available windows.
- **Custom Delays**: Set unique wait times for each individual click point.
- **DPI Awareness**: Accurate positioning on high-resolution displays.
- **Emergency Stop**: Press **Esc** at any time to stop the clicking loop.

## Usage

1. **Choose Mode**: Use the tabs at the top to switch between **Screen Mode**, **Window Mode**, and **Settings**.
2. **Optional Window Setting**: In **Settings**, enable **Pure background clicking** if window-mode clicks must never use real mouse input. This limits window dots to the target window's client area.
3. **Add Targets**:
   - In **Screen Mode**, click "Add Dot".
   - In **Window Mode**, click "Add Window" to pick a target (the list refreshes automatically). Once added, the window is automatically selected so you can immediately click "Add Dot".
4. **Position Dots**: Drag the numbered dots to your desired locations.
5. **Configure Sequence**: Adjust the order using Up/Down buttons and set custom post-click delays.
6. **Set Execution**: Toggle the **Loop** checkbox to enable or disable continuous clicking.
7. **Save/Load**: Use **Export** to save your configuration and **Import** to load a previously saved setup.
8. **Auto-run Setup**: Use **Auto Config** to import a script or save the current setup for `--auto --silent`. For looped auto configs, set the timeout and max-round safety limits.
9. **Run**: Click **Start**. Press **Esc** to stop.

## Build Executable

You can compile this tool into a standalone executable using `nuitka`:

```bash
nuitka --standalone --onefile --windows-console-mode=disable --enable-plugin=tk-inter main.py
```

*Note: Requires `pywin32` and `pydirectinput` to be installed in the build environment.*
