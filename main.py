import ctypes
from ctypes import wintypes
import threading
import tkinter as tk
from tkinter import ttk, messagebox

import pydirectinput

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

WH_MOUSE_LL = 14
WM_LBUTTONDOWN = 0x0201
WM_RBUTTONDOWN = 0x0204
WM_QUIT = 0x0012
HC_ACTION = 0
VK_ESCAPE = 0x1B


PROCESS_PER_MONITOR_DPI_AWARE = 2
DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = ctypes.c_void_p(-4)


def enable_dpi_awareness() -> None:
    try:
        user32.SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2)
        return
    except (AttributeError, OSError):
        pass

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(PROCESS_PER_MONITOR_DPI_AWARE)
    except (AttributeError, OSError):
        pass


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("pt", POINT),
        ("mouseData", ctypes.c_ulong),
        ("flags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.c_void_p),
    ]


LowLevelMouseProc = ctypes.WINFUNCTYPE(
    wintypes.LPARAM, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM
)

user32.SetWindowsHookExW.restype = wintypes.HHOOK
user32.SetWindowsHookExW.argtypes = [
    ctypes.c_int,
    LowLevelMouseProc,
    wintypes.HINSTANCE,
    wintypes.DWORD,
]
user32.CallNextHookEx.restype = wintypes.LPARAM
user32.CallNextHookEx.argtypes = [
    wintypes.HHOOK,
    ctypes.c_int,
    wintypes.WPARAM,
    wintypes.LPARAM,
]
user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
user32.GetMessageW.argtypes = [
    ctypes.POINTER(wintypes.MSG),
    wintypes.HWND,
    wintypes.UINT,
    wintypes.UINT,
]
user32.PostThreadMessageW.argtypes = [
    wintypes.DWORD,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
]
user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = ctypes.c_short
kernel32.GetCurrentThreadId.restype = wintypes.DWORD
kernel32.GetModuleHandleW.restype = wintypes.HMODULE
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]


DOT_SIZE = 40

class DraggableDot(tk.Toplevel):
    """A semi-transparent, numbered, draggable dot that stays on top."""
    def __init__(self, master, index, x, y, on_move):
        super().__init__(master)
        self.index = index  # 0-based index
        self.on_move = on_move
        
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.7)
        
        # Initialize position
        self.update_position(x, y)
        
        # We use a canvas to draw a nice circle and number
        self.canvas = tk.Canvas(self, width=DOT_SIZE, height=DOT_SIZE, highlightthickness=0, bg='white')
        self.canvas.pack()
        
        # Make white background transparent
        self.config(bg='white')
        self.attributes("-transparentcolor", "white")
        
        # 1. Outer halo border (Light Blue)
        self.halo = self.canvas.create_oval(2, 2, DOT_SIZE-2, DOT_SIZE-2, fill="#87CEFA", outline="")
        
        # 2. Main Dot (Primary Blue)
        inner_m = 6
        self.circle = self.canvas.create_oval(inner_m, inner_m, DOT_SIZE-inner_m, DOT_SIZE-inner_m, fill="#0078d7", outline="white", width=1)
        
        # 3. Sequence Number
        self.text = self.canvas.create_text(DOT_SIZE//2, DOT_SIZE//2, text=str(index+1), fill="white", font=("Arial", 10, "bold"))
        
        self.canvas.bind("<Button-1>", self._on_start)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        
    def update_position(self, x, y):
        """Update window geometry based on center coordinate."""
        self.geometry(f"{DOT_SIZE}x{DOT_SIZE}+{int(x - DOT_SIZE/2)}+{int(y - DOT_SIZE/2)}")

    def set_number(self, num):
        """Update the displayed sequence number."""
        self.canvas.itemconfig(self.text, text=str(num))

    def _on_start(self, event):
        self._drag_data = {"x": event.x, "y": event.y}

    def _on_drag(self, event):
        dx = event.x - self._drag_data["x"]
        dy = event.y - self._drag_data["y"]
        # winfo_x/y is top-left, we want center
        new_x = self.winfo_x() + dx + DOT_SIZE//2
        new_y = self.winfo_y() + dy + DOT_SIZE//2
        self.update_position(new_x, new_y)
        self.on_move(self.index, new_x, new_y)


class ClickerApp:
    def __init__(self) -> None:
        enable_dpi_awareness()
        self.root = tk.Tk()
        self.root.title("Mouse Click Tool")
        self.root.resizable(False, False)

        self.interval_var = tk.StringVar(value="500")
        self.step_delay_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready")
        
        # List of dicts: {"x": int, "y": int, "delay": int|None, "dot": DraggableDot}
        self._positions: list[dict] = []
        
        self._stop_event = threading.Event()
        self._click_thread: threading.Thread | None = None
        self._escape_thread: threading.Thread | None = None

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_ui(self) -> None:
        frame = ttk.Frame(self.root, padding=16)
        frame.grid(sticky="nsew")

        # Row 0: Global Interval
        ttk.Label(frame, text="Global Interval (ms)").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.interval_var, width=12).grid(
            row=0, column=1, padx=(8, 0), sticky="w"
        )

        # Row 1: Position List Label
        ttk.Label(frame, text="Click Order & Positions").grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(12, 4)
        )

        # Row 2: Listbox
        list_frame = ttk.Frame(frame)
        list_frame.grid(row=2, column=0, columnspan=2, sticky="ew")
        self.position_list = tk.Listbox(
            list_frame, height=8, width=40, activestyle="dotbox"
        )
        self.position_list.grid(row=0, column=0)
        self.position_list.bind("<<ListboxSelect>>", self._on_list_select)
        
        scrollbar = ttk.Scrollbar(
            list_frame, orient="vertical", command=self.position_list.yview
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.position_list.config(yscrollcommand=scrollbar.set)

        # Row 3: Selected Item Properties
        prop_frame = ttk.LabelFrame(frame, text="Selected Position Properties", padding=8)
        prop_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        
        ttk.Label(prop_frame, text="Wait after (ms):").grid(row=0, column=0, sticky="w")
        ttk.Entry(prop_frame, textvariable=self.step_delay_var, width=10).grid(row=0, column=1, padx=4)
        ttk.Button(prop_frame, text="Apply", command=self.apply_step_delay).grid(row=0, column=2)
        ttk.Label(prop_frame, text="(Empty = use global interval)", font=("", 8), foreground="#666666").grid(row=1, column=0, columnspan=3, sticky="w")

        # Row 4: Controls
        edit_row = ttk.Frame(frame)
        edit_row.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        ttk.Button(edit_row, text="Add Dot", command=self.add_dot).grid(row=0, column=0, padx=(0, 6))
        ttk.Button(edit_row, text="Remove", command=self.remove_position).grid(row=0, column=1, padx=6)
        ttk.Button(edit_row, text="Up", width=4, command=lambda: self.move_position(-1)).grid(row=0, column=2, padx=(6, 0))
        ttk.Button(edit_row, text="Down", width=5, command=lambda: self.move_position(1)).grid(row=0, column=3, padx=(4, 0))
        ttk.Button(edit_row, text="Clear", command=self.clear_positions).grid(row=0, column=4, padx=(6, 0))

        # Row 5: Run controls
        run_row = ttk.Frame(frame)
        run_row.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        self.start_button = ttk.Button(run_row, text="Start Loop", command=self.start_clicking)
        self.start_button.grid(row=0, column=0, padx=(0, 8))
        self.stop_button = ttk.Button(run_row, text="Stop", command=self.stop_clicking, state="disabled")
        self.stop_button.grid(row=0, column=1)

        # Row 6: Status
        ttk.Label(frame, textvariable=self.status_var, foreground="#005a9e", font=("", 9, "bold")).grid(
            row=6, column=0, columnspan=2, sticky="w", pady=(12, 0)
        )
        ttk.Label(
            frame,
            text="Drag dots to set positions. Press Esc to stop clicking.",
            foreground="#666666",
        ).grid(row=7, column=0, columnspan=2, sticky="w", pady=(4, 0))

    def add_dot(self) -> None:
        """Create a new draggable dot at the center of the screen."""
        screen_w = user32.GetSystemMetrics(0)
        screen_h = user32.GetSystemMetrics(1)
        x, y = screen_w // 2, screen_h // 2
        
        index = len(self._positions)
        dot = DraggableDot(self.root, index, x, y, self._on_dot_move)
        
        self._positions.append({
            "x": x,
            "y": y,
            "delay": None,
            "dot": dot
        })
        self._refresh_list()
        self.position_list.selection_clear(0, "end")
        self.position_list.selection_set(index)
        self.position_list.activate(index)
        self._on_list_select()
        self.status_var.set(f"Added dot {index+1} at center.")

    def _on_dot_move(self, index, x, y):
        """Callback when a dot is dragged."""
        self._positions[index]["x"] = x
        self._positions[index]["y"] = y
        self._refresh_list_item(index)

    def _on_list_select(self, event=None):
        """Update the property fields when a position is selected in the list."""
        sel = self.position_list.curselection()
        if not sel:
            return
        pos = self._positions[sel[0]]
        delay = pos["delay"]
        self.step_delay_var.set(str(delay) if delay is not None else "")

    def apply_step_delay(self):
        """Save the custom delay for the selected position."""
        sel = self.position_list.curselection()
        if not sel:
            messagebox.showinfo("Selection Required", "Select a position first.")
            return
        
        val = self.step_delay_var.get().strip()
        index = sel[0]
        if not val:
            self._positions[index]["delay"] = None
        else:
            try:
                ms = int(val)
                if ms < 0: raise ValueError
                self._positions[index]["delay"] = ms
            except ValueError:
                messagebox.showerror("Invalid Value", "Enter a non-negative integer for milliseconds.")
                return
        
        self._refresh_list_item(index)
        self.status_var.set(f"Updated delay for item {index+1}.")

    def remove_position(self) -> None:
        sel = self.position_list.curselection()
        if not sel:
            return
        index = sel[0]
        self._positions[index]["dot"].destroy()
        del self._positions[index]
        
        # Update sequence numbers for remaining dots
        for i in range(index, len(self._positions)):
            self._positions[i]["dot"].index = i
            self._positions[i]["dot"].set_number(i + 1)
            
        self._refresh_list()

    def move_position(self, delta: int) -> None:
        sel = self.position_list.curselection()
        if not sel:
            return
        index = sel[0]
        target = index + delta
        if not 0 <= target < len(self._positions):
            return
            
        # Swap in the data list
        self._positions[index], self._positions[target] = (
            self._positions[target],
            self._positions[index],
        )
        
        # Sync dot indices and labels
        self._positions[index]["dot"].index = index
        self._positions[index]["dot"].set_number(index + 1)
        self._positions[target]["dot"].index = target
        self._positions[target]["dot"].set_number(target + 1)
        
        self._refresh_list()
        self.position_list.selection_set(target)
        self.position_list.activate(target)
        self._on_list_select()

    def clear_positions(self) -> None:
        for p in self._positions:
            p["dot"].destroy()
        self._positions.clear()
        self._refresh_list()

    def _refresh_list(self) -> None:
        self.position_list.delete(0, "end")
        for i in range(len(self._positions)):
            self._refresh_list_item(i, append=True)

    def _refresh_list_item(self, index, append=False):
        pos = self._positions[index]
        delay_str = f" [Wait: {pos['delay']}ms]" if pos['delay'] is not None else ""
        text = f"{index+1}: ({int(pos['x'])}, {int(pos['y'])}){delay_str}"
        
        if append:
            self.position_list.insert("end", text)
        else:
            self.position_list.delete(index)
            self.position_list.insert(index, text)
            # Re-select if it was selected
            # Note: simplified, might lose focus but works for basic needs

    def start_clicking(self) -> None:
        if self._click_thread and self._click_thread.is_alive():
            return
        if not self._positions:
            messagebox.showerror("No positions", "Add at least one dot first.")
            return
        try:
            global_interval = int(self.interval_var.get())
            if global_interval < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid interval", "Enter a non-negative whole number for global interval.")
            return

        self._stop_event.clear()
        
        # Snapshot positions for the thread
        positions_snapshot = []
        for p in self._positions:
            positions_snapshot.append({
                "x": p["x"],
                "y": p["y"],
                "delay": p["delay"]
            })
            
        # Hide dots while clicking to avoid blocking
        self._set_dots_visible(False)
        
        self._click_thread = threading.Thread(
            target=self._click_loop, args=(global_interval, positions_snapshot), daemon=True
        )
        self._click_thread.start()
        
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self._escape_thread = threading.Thread(target=self._watch_escape, daemon=True)
        self._escape_thread.start()
        self.status_var.set("Looping clicks... Press Esc to stop.")

    def stop_clicking(self) -> None:
        self._stop_event.set()

    def _set_dots_visible(self, visible: bool):
        for p in self._positions:
            if visible:
                p["dot"].deiconify()
            else:
                p["dot"].withdraw()

    def _watch_escape(self) -> None:
        while not self._stop_event.wait(0.03):
            if user32.GetAsyncKeyState(VK_ESCAPE) & 0x8000:
                self._stop_event.set()
                break

    def _click_loop(self, global_interval_ms: int, positions: list[dict]) -> None:
        global_interval_s = global_interval_ms / 1000.0
        while not self._stop_event.is_set():
            for pos in positions:
                if self._stop_event.is_set():
                    break
                
                self._click_at(pos["x"], pos["y"])
                
                # Determine wait time: per-step delay or global interval
                delay_ms = pos["delay"] if pos["delay"] is not None else global_interval_ms
                wait_s = delay_ms / 1000.0
                
                if wait_s > 0 and self._stop_event.wait(wait_s):
                    break
                    
        self.root.after(0, self._on_loop_exit)

    def _on_loop_exit(self) -> None:
        self._set_dots_visible(True)
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        self.status_var.set("Stopped")

    def _click_at(self, x: int, y: int) -> None:
        """Move and click with a small duration for better compatibility."""
        pydirectinput.click(x=int(x), y=int(y), duration=0.05)

    def on_close(self) -> None:
        self._stop_event.set()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    ClickerApp().run()
