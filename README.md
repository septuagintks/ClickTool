# Click Tool (Minified)

A lightweight, zero-dependency Windows mouse auto-clicker with visual draggable targets. This version uses direct Windows API calls via `ctypes` to ensure maximum portability without external libraries.

## Run

1.  Ensure you have Python installed.
2.  Start the app:

    ```bash
    python main.py
    ```

## Features

### 1. Screen Mode
- **Global Coordinates**: Set click points anywhere on the screen.
- **Draggable Targets**: Visually position numbered dots.
- **Hardware Simulation**: Uses `SendInput` for compatibility with games and sensitive apps.

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
- **Auto-refreshing Window List**: The "Add Window" dialog automatically updates the list of available windows.
- **Custom Delays**: Set unique wait times for each individual click point.
- **DPI Awareness**: Accurate positioning on high-resolution displays.
- **Emergency Stop**: Press **Esc** at any time to stop the clicking loop.

## Usage

1. **Choose Mode**: Use the tabs at the top to switch between **Screen Mode** and **Window Mode**.
2. **Add Targets**:
   - In **Screen Mode**, click "Add Dot".
   - In **Window Mode**, click "Add Window" to pick a target. Once added, click "Add Dot".
3. **Position Dots**: Drag the numbered dots to your desired locations.
4. **Configure Sequence**: Adjust the order using Up/Down buttons and set custom post-click delays.
5. **Set Execution**: Toggle the **Loop** checkbox to enable or disable continuous clicking.
6. **Save/Load**: Use **Export Script** to save your configuration and **Import Script** to load it later.
7. **Run**: Click **Start**. Press **Esc** to stop.

## Dependencies
- **None**: This is the lightweight version using direct Windows API calls.
- Standard libraries used: `tkinter`, `json`, `threading`, `ctypes`, `time`.

## Build Executable

You can compile this tool into a standalone executable using `nuitka`:

```bash
nuitka --onefile --windows-console-mode=disable main.py
```
