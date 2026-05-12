# click-tool

A small Windows mouse auto-clicker with a Tkinter window.

## Run

1. Activate the virtual environment:

   ```bash
   .venv\Scripts\activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Start the app:

   ```bash
   python main.py
   ```

## Usage

1.  **Set Interval**: Enter the global click interval in milliseconds at the top.
2.  **Add Positions**:
    *   Click **Add Dot** to generate a semi-transparent draggable dot in the center of the screen.
    *   Drag the dot to your desired click target. The number on the dot indicates its order in the sequence.
3.  **Manage List**:
    *   Use **Up**, **Down**, and **Remove** to adjust the order or delete positions.
    *   **Wait after (ms)**: Select a position in the list and enter a millisecond value to set a custom wait time *after* that specific click. If left empty, it defaults to the global interval.
4.  **Run**:
    *   Click **Start Loop** to begin clicking. The dots will automatically hide during the loop.
    *   Press **Esc** or click **Stop** to end the sequence.

## Notes

- This version is Windows-only.
- Clicking is performed via `pydirectinput` with a small hold duration for better compatibility with games and UI elements.
- The app is DPI-aware to ensure dots align correctly with screen coordinates.
