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
- **Enhanced Background Clicking**: Uses `PostMessage` and child-window detection to click windows even when they are not in the foreground.
- **Full Window Range**: Draggable dots cover the entire window area, including the title bar.
- **Smart Constraints**: Dots are locked within the window boundaries and follow the window as it moves or resizes.
- **Cross-Window Sequencing**: Create sequences across multiple different windows.

### UI & UX Improvements
- **Optimized Focus**: Focus stays on the window list when adding dots for rapid setup.
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

1. **Choose Mode**: Use the tabs at the top to switch between **Screen Mode** and **Window Mode**.
2. **Add Targets**:
   - In **Screen Mode**, click "Add Dot".
   - In **Window Mode**, click "Add Window" to pick a target (the list refreshes automatically). Once added, the window is automatically selected so you can immediately click "Add Dot".
3. **Position Dots**: Drag the numbered dots to your desired locations.
4. **Configure Sequence**: Adjust the order using Up/Down buttons and set custom post-click delays.
5. **Set Execution**: Toggle the **Loop** checkbox to enable or disable continuous clicking.
6. **Save/Load**: Use **Export Script** to save your configuration and **Import Script** to load a previously saved setup.
7. **Auto-run Setup**: Use **Auto Config** to import a script or save the current setup for `--auto --silent`. For looped auto configs, set the timeout and max-round safety limits.
8. **Run**: Click **Start**. Press **Esc** to stop.

## Build Executable

You can compile this tool into a standalone executable using `nuitka`:

```bash
nuitka --standalone --onefile --windows-console-mode=disable --enable-plugin=tk-inter main.py
```

*Note: Requires `pywin32` and `pydirectinput` to be installed in the build environment.*
