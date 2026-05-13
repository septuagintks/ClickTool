import ctypes
from ctypes import wintypes
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import time

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# WinAPI Constants
WH_MOUSE_LL = 14
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_RBUTTONDOWN = 0x0204
WM_QUIT = 0x0012
HC_ACTION = 0
VK_ESCAPE = 0x1B
MK_LBUTTON = 0x0001

INPUT_MOUSE = 0
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_ABSOLUTE = 0x8000
SM_CXSCREEN = 0
SM_CYSCREEN = 1

PROCESS_PER_MONITOR_DPI_AWARE = 2
DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = ctypes.c_void_p(-4)

# WinAPI Structures
class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", ctypes.c_ulong),
        ("wParamL", ctypes.c_ushort),
        ("wParamH", ctypes.c_ushort),
    ]

class INPUT_UNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]

class INPUT(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("iu", INPUT_UNION)]

# WinAPI Function Prototypes
user32.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_void_p]
user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
user32.SendInput.restype = wintypes.UINT
user32.GetSystemMetrics.argtypes = [ctypes.c_int]
user32.GetSystemMetrics.restype = ctypes.c_int
user32.ChildWindowFromPointEx.argtypes = [wintypes.HWND, POINT, wintypes.UINT]
user32.ChildWindowFromPointEx.restype = wintypes.HWND
user32.ScreenToClient.argtypes = [wintypes.HWND, ctypes.POINTER(POINT)]
user32.ScreenToClient.restype = wintypes.BOOL

CWP_ALL = 0x0000
CWP_SKIPINVISIBLE = 0x0001

def makelong(low, high):
    return (low & 0xFFFF) | ((high & 0xFFFF) << 16)

def send_mouse_click(x, y):
    """Perform a hardware-level click using SendInput."""
    screen_w = user32.GetSystemMetrics(SM_CXSCREEN)
    screen_h = user32.GetSystemMetrics(SM_CYSCREEN)
    
    # Normalized coordinates (0-65535)
    nx = int(x * 65535 / (screen_w - 1))
    ny = int(y * 65535 / (screen_h - 1))
    
    # Move
    inp_move = INPUT()
    inp_move.type = INPUT_MOUSE
    inp_move.iu.mi = MOUSEINPUT(nx, ny, 0, MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, 0, None)
    
    # Down
    inp_down = INPUT()
    inp_down.type = INPUT_MOUSE
    inp_down.iu.mi = MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTDOWN, 0, None)
    
    # Up
    inp_up = INPUT()
    inp_up.type = INPUT_MOUSE
    inp_up.iu.mi = MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTUP, 0, None)
    
    inputs = (INPUT * 3)(inp_move, inp_down, inp_up)
    user32.SendInput(3, inputs, ctypes.sizeof(INPUT))

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

class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]

user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(RECT)]
user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(RECT)]
user32.IsWindow.argtypes = [wintypes.HWND]
user32.IsWindow.restype = wintypes.BOOL
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsWindowVisible.restype = wintypes.BOOL
user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(POINT)]

EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
user32.EnumWindows.argtypes = [EnumWindowsProc, wintypes.LPARAM]

user32.IsIconic.argtypes = [wintypes.HWND]
user32.IsIconic.restype = wintypes.BOOL

def get_window_title(hwnd):
    length = user32.GetWindowTextLengthW(hwnd)
    buff = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buff, length + 1)
    return buff.value

def get_window_rect(hwnd):
    rect = RECT()
    if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return rect.left, rect.top, rect.right, rect.bottom
    return None

def get_client_rect(hwnd):
    rect = RECT()
    if user32.GetClientRect(hwnd, ctypes.byref(rect)):
        return rect.left, rect.top, rect.right, rect.bottom
    return None

def client_to_screen(hwnd, x, y):
    pt = POINT(x, y)
    user32.ClientToScreen(hwnd, ctypes.byref(pt))
    return pt.x, pt.y

class DraggableDot(tk.Toplevel):
    """A semi-transparent, numbered, draggable dot that stays on top."""
    def __init__(self, master, index, x, y, on_move, on_click=None, hwnd=None):
        super().__init__(master)
        self.index = index  # 0-based index
        self.on_move = on_move
        self.on_click = on_click
        self.hwnd = hwnd # If set, x and y are relative to this window's top-left
        
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.7)
        
        # Initialize position
        if self.hwnd:
            rect = get_window_rect(self.hwnd)
            if rect:
                sx = rect[0] + x
                sy = rect[1] + y
                self.update_position(sx, sy)
            else:
                self.update_position(x, y)
        else:
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
        if self.on_click:
            self.on_click(self.index)

    def _on_drag(self, event):
        dx = event.x - self._drag_data["x"]
        dy = event.y - self._drag_data["y"]
        # winfo_x/y is top-left, we want center
        new_screen_x = self.winfo_x() + dx + DOT_SIZE//2
        new_screen_y = self.winfo_y() + dy + DOT_SIZE//2
        
        if self.hwnd:
            rect = get_window_rect(self.hwnd)
            if rect:
                # Constrain within window rect
                new_screen_x = max(rect[0], min(new_screen_x, rect[2]))
                new_screen_y = max(rect[1], min(new_screen_y, rect[3]))
                
                rel_x = new_screen_x - rect[0]
                rel_y = new_screen_y - rect[1]
                self.update_position(new_screen_x, new_screen_y)
                self.on_move(self.index, rel_x, rel_y)
            else:
                self.update_position(new_screen_x, new_screen_y)
                self.on_move(self.index, new_screen_x, new_screen_y)
        else:
            self.update_position(new_screen_x, new_screen_y)
            self.on_move(self.index, new_screen_x, new_screen_y)


class ClickerApp:
    def __init__(self) -> None:
        enable_dpi_awareness()
        self.root = tk.Tk()
        self.root.title("Mouse Click Tool")
        self.root.resizable(False, False)

        self.interval_var = tk.StringVar(value="500")
        self.step_delay_var = tk.StringVar()
        self.loop_var = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value="Ready")
        
        # Screen Mode State
        self._screen_positions: list[dict] = []
        
        # Window Mode State
        self._window_positions: list[dict] = []
        self._target_windows: list[dict] = [] # {"hwnd": int, "title": str}
        
        self._stop_event = threading.Event()
        self._click_thread: threading.Thread | None = None
        self._escape_thread: threading.Thread | None = None

        self._build_ui()
        self.sync_dots_loop()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_ui(self) -> None:
        # Notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True)
        
        # Screen Mode Tab
        self.screen_frame = ttk.Frame(self.notebook, padding=16)
        self.notebook.add(self.screen_frame, text="Screen Mode")
        self._build_screen_mode_ui(self.screen_frame)
        
        # Window Mode Tab
        self.window_frame = ttk.Frame(self.notebook, padding=16)
        self.notebook.add(self.window_frame, text="Window Mode")
        self._build_window_mode_ui(self.window_frame)

        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        # Global Run controls and Status
        bottom_frame = ttk.Frame(self.root, padding=(16, 0, 16, 16))
        bottom_frame.pack(fill="x")
        
        ttk.Label(bottom_frame, text="Global Interval (ms)").grid(row=0, column=0, sticky="w")
        ttk.Entry(bottom_frame, textvariable=self.interval_var, width=12).grid(
            row=0, column=1, padx=(8, 0), sticky="w"
        )
        ttk.Checkbutton(bottom_frame, text="Loop", variable=self.loop_var).grid(row=0, column=2, padx=(12, 0))
        
        run_row = ttk.Frame(bottom_frame)
        run_row.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(12, 0))
        self.start_button = ttk.Button(run_row, text="Start", command=self.start_clicking)
        self.start_button.grid(row=0, column=0, padx=(0, 8))
        self.stop_button = ttk.Button(run_row, text="Stop", command=self.stop_clicking, state="disabled")
        self.stop_button.grid(row=0, column=1, padx=(0, 8))
        
        ttk.Button(run_row, text="Import Script", command=self.import_script).grid(row=0, column=2, padx=(8, 0))
        ttk.Button(run_row, text="Export Script", command=self.export_script).grid(row=0, column=3, padx=(4, 0))

        ttk.Label(bottom_frame, textvariable=self.status_var, foreground="#005a9e", font=("", 9, "bold")).grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(12, 0)
        )
        ttk.Label(
            bottom_frame,
            text="Drag dots to set positions. Press Esc to stop clicking.",
            foreground="#666666",
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(4, 0))

    def _build_screen_mode_ui(self, frame) -> None:
        # Row 1: Position List Label
        ttk.Label(frame, text="Click Order & Positions").grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(0, 4)
        )

        # Row 2: Listbox
        list_frame = ttk.Frame(frame)
        list_frame.grid(row=2, column=0, columnspan=2, sticky="ew")
        self.screen_list = tk.Listbox(
            list_frame, height=8, width=50, activestyle="dotbox"
        )
        self.screen_list.grid(row=0, column=0)
        self.screen_list.bind("<<ListboxSelect>>", self._on_screen_list_select)
        
        scrollbar = ttk.Scrollbar(
            list_frame, orient="vertical", command=self.screen_list.yview
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.screen_list.config(yscrollcommand=scrollbar.set)

        # Row 3: Selected Item Properties
        prop_frame = ttk.LabelFrame(frame, text="Selected Position Properties", padding=8)
        prop_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        
        ttk.Label(prop_frame, text="Wait after (ms):").grid(row=0, column=0, sticky="w")
        self.screen_step_delay_entry = ttk.Entry(prop_frame, textvariable=self.step_delay_var, width=10)
        self.screen_step_delay_entry.grid(row=0, column=1, padx=4)
        ttk.Button(prop_frame, text="Apply", command=self.apply_step_delay).grid(row=0, column=2)
        ttk.Label(prop_frame, text="(Empty = use global interval)", font=("", 8), foreground="#666666").grid(row=1, column=0, columnspan=3, sticky="w")

        # Row 4: Controls
        edit_row = ttk.Frame(frame)
        edit_row.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        ttk.Button(edit_row, text="Add Dot", command=self.add_screen_dot).grid(row=0, column=0, padx=(0, 6))
        ttk.Button(edit_row, text="Remove", command=self.remove_screen_position).grid(row=0, column=1, padx=6)
        ttk.Button(edit_row, text="Up", width=4, command=lambda: self.move_screen_position(-1)).grid(row=0, column=2, padx=(6, 0))
        ttk.Button(edit_row, text="Down", width=5, command=lambda: self.move_screen_position(1)).grid(row=0, column=3, padx=(4, 0))
        ttk.Button(edit_row, text="Clear", command=self.clear_screen_positions).grid(row=0, column=4, padx=(6, 0))

    def _build_window_mode_ui(self, frame) -> None:
        # Two columns: Window Column and Click Point Column
        paned = ttk.PanedWindow(frame, orient="horizontal")
        paned.grid(row=0, column=0, sticky="nsew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        
        # Left: Window Column
        win_frame = ttk.Frame(paned, padding=(0, 0, 8, 0))
        paned.add(win_frame, weight=1)
        
        ttk.Label(win_frame, text="Target Windows").pack(anchor="w")
        
        win_list_frame = ttk.Frame(win_frame)
        win_list_frame.pack(fill="both", expand=True, pady=4)
        
        self.target_win_list = tk.Listbox(win_list_frame, height=10, width=30)
        self.target_win_list.pack(side="left", fill="both", expand=True)
        
        win_scroll = ttk.Scrollbar(win_list_frame, orient="vertical", command=self.target_win_list.yview)
        win_scroll.pack(side="right", fill="y")
        self.target_win_list.config(yscrollcommand=win_scroll.set)
        
        win_btn_row = ttk.Frame(win_frame)
        win_btn_row.pack(fill="x")
        ttk.Button(win_btn_row, text="Add Window", command=self.add_target_window).pack(side="left", padx=2)
        ttk.Button(win_btn_row, text="Remove", command=self.remove_target_window).pack(side="left", padx=2)
        
        # Right: Click Point Column
        pt_frame = ttk.Frame(paned, padding=(8, 0, 0, 0))
        paned.add(pt_frame, weight=2)
        
        ttk.Label(pt_frame, text="Click Points (Cross-window sorting allowed)").pack(anchor="w")
        
        pt_list_frame = ttk.Frame(pt_frame)
        pt_list_frame.pack(fill="both", expand=True, pady=4)
        
        self.window_pt_list = tk.Listbox(pt_list_frame, height=10, width=40)
        self.window_pt_list.pack(side="left", fill="both", expand=True)
        self.window_pt_list.bind("<<ListboxSelect>>", self._on_window_list_select)
        
        pt_scroll = ttk.Scrollbar(pt_list_frame, orient="vertical", command=self.window_pt_list.yview)
        pt_scroll.pack(side="right", fill="y")
        self.window_pt_list.config(yscrollcommand=pt_scroll.set)
        
        pt_btn_row = ttk.Frame(pt_frame)
        pt_btn_row.pack(fill="x")
        ttk.Button(pt_btn_row, text="Add Dot", command=self.add_window_dot).pack(side="left", padx=2)
        ttk.Button(pt_btn_row, text="Remove", command=self.remove_window_position).pack(side="left", padx=2)
        ttk.Button(pt_btn_row, text="Up", width=4, command=lambda: self.move_window_position(-1)).pack(side="left", padx=2)
        ttk.Button(pt_btn_row, text="Down", width=5, command=lambda: self.move_window_position(1)).pack(side="left", padx=2)
        ttk.Button(pt_btn_row, text="Clear", command=self.clear_window_positions).pack(side="left", padx=2)

        # Selected Item Properties for Window Mode
        win_prop_frame = ttk.LabelFrame(pt_frame, text="Selected Position Properties", padding=8)
        win_prop_frame.pack(fill="x", pady=(8, 0))
        
        ttk.Label(win_prop_frame, text="Wait after (ms):").grid(row=0, column=0, sticky="w")
        self.window_step_delay_entry = ttk.Entry(win_prop_frame, textvariable=self.step_delay_var, width=10)
        self.window_step_delay_entry.grid(row=0, column=1, padx=4)
        ttk.Button(win_prop_frame, text="Apply", command=self.apply_step_delay).grid(row=0, column=2)

    def _on_tab_changed(self, event):
        """Show only the dots belonging to the active tab."""
        # If clicking is active, dots are already hidden
        if self._click_thread and self._click_thread.is_alive():
            return
            
        current_tab = self.notebook.index(self.notebook.select())
        if current_tab == 0: # Screen
            for p in self._screen_positions: p["dot"].deiconify()
            for p in self._window_positions: p["dot"].withdraw()
        else: # Window
            for p in self._screen_positions: p["dot"].withdraw()
            for p in self._window_positions: p["dot"].deiconify()
            
    def sync_dots_loop(self):
        """Update window-based dots to follow their windows and prevent overflow."""
        # Only sync if we are not clicking
        is_clicking = self._click_thread and self._click_thread.is_alive()
        current_tab = self.notebook.index(self.notebook.select())
        
        if current_tab == 1 and not is_clicking:
            for p in self._window_positions:
                hwnd = p.get("hwnd")
                if hwnd and user32.IsWindow(hwnd):
                    if user32.IsIconic(hwnd):
                        p["dot"].withdraw()
                    else:
                        rect = get_window_rect(hwnd)
                        if rect:
                            # Clamp relative coordinates to current window size
                            ww = rect[2] - rect[0]
                            wh = rect[3] - rect[1]
                            p["x"] = max(0, min(p["x"], ww))
                            p["y"] = max(0, min(p["y"], wh))
                            
                            sx = rect[0] + p["x"]
                            sy = rect[1] + p["y"]
                            p["dot"].deiconify()
                            p["dot"].update_position(sx, sy)
                        else:
                            p["dot"].withdraw()
                else:
                    p["dot"].withdraw()
        
        self.root.after(100, self.sync_dots_loop)

    def add_target_window(self):
        """Open a dialog to select a window from all visible windows."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Select Window (Auto-refreshing)")
        dialog.geometry("400x500")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Select a window from the list:").pack(pady=8)
        
        list_frame = ttk.Frame(dialog)
        list_frame.pack(fill="both", expand=True, padx=8)
        
        lb = tk.Listbox(list_frame)
        lb.pack(side="left", fill="both", expand=True)
        
        scroll = ttk.Scrollbar(list_frame, orient="vertical", command=lb.yview)
        scroll.pack(side="right", fill="y")
        lb.config(yscrollcommand=scroll.set)
        
        current_windows = []
        
        def refresh_list():
            if not dialog.winfo_exists():
                return
                
            nonlocal current_windows
            new_windows = []
            def enum_callback(hwnd, lparam):
                if user32.IsWindowVisible(hwnd):
                    title = get_window_title(hwnd)
                    if title:
                        new_windows.append((hwnd, title))
                return True
                
            enum_proc = EnumWindowsProc(enum_callback)
            user32.EnumWindows(enum_proc, 0)
            new_windows.sort(key=lambda x: x[1].lower())
            
            # Update only if changed to preserve selection if possible
            if new_windows != current_windows:
                sel = lb.curselection()
                selected_hwnd = current_windows[sel[0]][0] if sel else None
                
                lb.delete(0, "end")
                for hwnd, title in new_windows:
                    lb.insert("end", title)
                    if hwnd == selected_hwnd:
                        new_idx = lb.size() - 1
                        lb.selection_set(new_idx)
                        lb.activate(new_idx)
                
                current_windows = new_windows
            
            dialog.after(1000, refresh_list)
            
        refresh_list()
            
        def on_select():
            sel = lb.curselection()
            if sel:
                hwnd, title = current_windows[sel[0]]
                # Check if already in list
                if any(w["hwnd"] == hwnd for w in self._target_windows):
                    messagebox.showinfo("Already Added", "This window is already in your target list.")
                else:
                    self._target_windows.append({"hwnd": hwnd, "title": title})
                    self._refresh_window_list()
                    # Select the newly added window
                    new_idx = len(self._target_windows) - 1
                    self.target_win_list.selection_clear(0, "end")
                    self.target_win_list.selection_set(new_idx)
                    self.target_win_list.activate(new_idx)
                dialog.destroy()
        
        ttk.Button(dialog, text="Select", command=on_select).pack(pady=8)
        ttk.Button(dialog, text="Cancel", command=dialog.destroy).pack(pady=(0, 8))

    def _refresh_window_list(self):
        self.target_win_list.delete(0, "end")
        for w in self._target_windows:
            self.target_win_list.insert("end", w["title"])

    def remove_target_window(self):
        sel = self.target_win_list.curselection()
        if not sel: return
        index = sel[0]
        hwnd = self._target_windows[index]["hwnd"]
        
        # Also remove any click points associated with this window
        to_remove = [i for i, p in enumerate(self._window_positions) if p.get("hwnd") == hwnd]
        for i in reversed(to_remove):
            self._window_positions[i]["dot"].destroy()
            del self._window_positions[i]
            
        del self._target_windows[index]
        self._refresh_window_list()
        self._refresh_window_pt_list()

    def add_screen_dot(self) -> None:
        """Create a new draggable dot at the center of the screen."""
        screen_w = user32.GetSystemMetrics(0)
        screen_h = user32.GetSystemMetrics(1)
        x, y = screen_w // 2, screen_h // 2
        
        index = len(self._screen_positions)
        dot = DraggableDot(self.root, index, x, y, self._on_screen_dot_move,
                          on_click=self._on_screen_dot_click)
        
        self._screen_positions.append({
            "x": x,
            "y": y,
            "delay": None,
            "dot": dot
        })
        self._refresh_screen_list()
        self.screen_list.selection_clear(0, "end")
        self.screen_list.selection_set(index)
        self.screen_list.activate(index)
        self._on_screen_list_select()
        self.status_var.set(f"Added screen dot {index+1} at center.")

    def _on_screen_dot_click(self, index):
        """Select corresponding item in list when dot is clicked."""
        self.notebook.select(0) # Ensure screen tab is active
        self.screen_list.selection_clear(0, "end")
        self.screen_list.selection_set(index)
        self.screen_list.activate(index)
        self._on_screen_list_select()

    def _on_screen_dot_move(self, index, x, y):
        """Callback when a screen dot is dragged."""
        self._screen_positions[index]["x"] = x
        self._screen_positions[index]["y"] = y
        self._refresh_screen_list_item(index)

    def _on_screen_list_select(self, event=None):
        """Update the property fields when a position is selected in the screen list."""
        sel = self.screen_list.curselection()
        if not sel:
            return
        pos = self._screen_positions[sel[0]]
        delay = pos["delay"]
        self.step_delay_var.set(str(delay) if delay is not None else "")

    def remove_screen_position(self) -> None:
        sel = self.screen_list.curselection()
        if not sel:
            return
        index = sel[0]
        self._screen_positions[index]["dot"].destroy()
        del self._screen_positions[index]
        
        # Update sequence numbers for remaining dots
        for i in range(index, len(self._screen_positions)):
            self._screen_positions[i]["dot"].index = i
            self._screen_positions[i]["dot"].set_number(i + 1)
            
        self._refresh_screen_list()

    def move_screen_position(self, delta: int) -> None:
        sel = self.screen_list.curselection()
        if not sel:
            return
        index = sel[0]
        target = index + delta
        if not 0 <= target < len(self._screen_positions):
            return
            
        # Swap in the data list
        self._screen_positions[index], self._screen_positions[target] = (
            self._screen_positions[target],
            self._screen_positions[index],
        )
        
        # Sync dot indices and labels
        self._screen_positions[index]["dot"].index = index
        self._screen_positions[index]["dot"].set_number(index + 1)
        self._screen_positions[target]["dot"].index = target
        self._screen_positions[target]["dot"].set_number(target + 1)
        
        self._refresh_screen_list()
        self.screen_list.selection_set(target)
        self.screen_list.activate(target)
        self._on_screen_list_select()

    def clear_screen_positions(self) -> None:
        for p in self._screen_positions:
            p["dot"].destroy()
        self._screen_positions.clear()
        self._refresh_screen_list()

    def _refresh_screen_list(self) -> None:
        self.screen_list.delete(0, "end")
        for i in range(len(self._screen_positions)):
            self._refresh_screen_list_item(i, append=True)

    def _refresh_screen_list_item(self, index, append=False):
        pos = self._screen_positions[index]
        delay_str = f" [Wait: {pos['delay']}ms]" if pos['delay'] is not None else ""
        text = f"{index+1}: ({int(pos['x'])}, {int(pos['y'])}){delay_str}"
        
        if append:
            self.screen_list.insert("end", text)
        else:
            self.screen_list.delete(index)
            self.screen_list.insert(index, text)

    def add_window_dot(self) -> None:
        """Create a new draggable dot for the selected window."""
        sel_win = self.target_win_list.curselection()
        if not sel_win:
            messagebox.showinfo("Select Window", "Select a target window from the left list first.")
            return
            
        win_idx = sel_win[0]
        win_data = self._target_windows[win_idx]
        hwnd = win_data["hwnd"]
        
        if not user32.IsWindow(hwnd):
            messagebox.showerror("Window Lost", "The selected window is no longer available.")
            return
            
        rect = get_window_rect(hwnd)
        if rect is None:
            messagebox.showerror("Error", "Could not get window position.")
            return
            
        # Place dot at center of window (including title bar)
        win_w = rect[2] - rect[0]
        win_h = rect[3] - rect[1]
        rel_x, rel_y = win_w // 2, win_h // 2
        
        index = len(self._window_positions)
        dot = DraggableDot(self.root, index, rel_x, rel_y, self._on_window_dot_move, 
                          on_click=self._on_window_dot_click, hwnd=hwnd)
        
        self._window_positions.append({
            "x": rel_x,
            "y": rel_y,
            "delay": None,
            "dot": dot,
            "hwnd": hwnd,
            "win_title": win_data["title"]
        })
        self._refresh_window_pt_list()
        
        # Keep focus on window list as requested
        self.target_win_list.selection_set(win_idx)
        self.target_win_list.activate(win_idx)
        
        self.status_var.set(f"Added window dot {index+1} for '{win_data['title']}'.")

    def _on_window_dot_click(self, index):
        """Select corresponding item in list when dot is clicked."""
        self.notebook.select(1) # Ensure window tab is active
        self.window_pt_list.selection_clear(0, "end")
        self.window_pt_list.selection_set(index)
        self.window_pt_list.activate(index)
        self.window_pt_list.see(index)
        self._on_window_list_select()

    def _on_window_dot_move(self, index, x, y):
        """Callback when a window dot is dragged (x, y are relative)."""
        self._window_positions[index]["x"] = x
        self._window_positions[index]["y"] = y
        self._refresh_window_pt_item(index)

    def _on_window_list_select(self, event=None):
        """Update the property fields when a position is selected in the window point list."""
        sel = self.window_pt_list.curselection()
        if not sel:
            return
        pos = self._window_positions[sel[0]]
        delay = pos["delay"]
        self.step_delay_var.set(str(delay) if delay is not None else "")

    def remove_window_position(self) -> None:
        sel = self.window_pt_list.curselection()
        if not sel:
            return
        index = sel[0]
        self._window_positions[index]["dot"].destroy()
        del self._window_positions[index]
        
        # Update sequence numbers for remaining dots
        for i in range(index, len(self._window_positions)):
            self._window_positions[i]["dot"].index = i
            self._window_positions[i]["dot"].set_number(i + 1)
            
        self._refresh_window_pt_list()

    def move_window_position(self, delta: int) -> None:
        sel = self.window_pt_list.curselection()
        if not sel:
            return
        index = sel[0]
        target = index + delta
        if not 0 <= target < len(self._window_positions):
            return
            
        self._window_positions[index], self._window_positions[target] = (
            self._window_positions[target],
            self._window_positions[index],
        )
        
        self._window_positions[index]["dot"].index = index
        self._window_positions[index]["dot"].set_number(index + 1)
        self._window_positions[target]["dot"].index = target
        self._window_positions[target]["dot"].set_number(target + 1)
        
        self._refresh_window_pt_list()
        self.window_pt_list.selection_set(target)
        self.window_pt_list.activate(target)
        self._on_window_list_select()

    def clear_window_positions(self) -> None:
        for p in self._window_positions:
            p["dot"].destroy()
        self._window_positions.clear()
        self._refresh_window_pt_list()

    def _refresh_window_pt_list(self) -> None:
        self.window_pt_list.delete(0, "end")
        for i in range(len(self._window_positions)):
            self._refresh_window_pt_item(i, append=True)

    def _refresh_window_pt_item(self, index, append=False):
        pos = self._window_positions[index]
        delay_str = f" [Wait: {pos['delay']}ms]" if pos['delay'] is not None else ""
        # Shorten title if too long
        title = (pos['win_title'][:15] + '..') if len(pos['win_title']) > 15 else pos['win_title']
        text = f"{index+1}: [{title}] ({int(pos['x'])}, {int(pos['y'])}){delay_str}"
        
        if append:
            self.window_pt_list.insert("end", text)
        else:
            self.window_pt_list.delete(index)
            self.window_pt_list.insert(index, text)

    def apply_step_delay(self):
        """Save the custom delay for the selected position in either mode."""
        current_tab = self.notebook.index(self.notebook.select())
        if current_tab == 0: # Screen
            sel = self.screen_list.curselection()
            positions = self._screen_positions
            refresh_fn = self._refresh_screen_list_item
        else: # Window
            sel = self.window_pt_list.curselection()
            positions = self._window_positions
            refresh_fn = self._refresh_window_pt_item
            
        if not sel:
            messagebox.showinfo("Selection Required", "Select a position first.")
            return
        
        val = self.step_delay_var.get().strip()
        index = sel[0]
        if not val:
            positions[index]["delay"] = None
        else:
            try:
                ms = int(val)
                if ms < 0: raise ValueError
                positions[index]["delay"] = ms
            except ValueError:
                messagebox.showerror("Invalid Value", "Enter a non-negative integer for milliseconds.")
                return
        
        refresh_fn(index)
        self.status_var.set(f"Updated delay for item {index+1}.")

    def start_clicking(self) -> None:
        if self._click_thread and self._click_thread.is_alive():
            return
            
        current_tab = self.notebook.index(self.notebook.select())
        if current_tab == 0:
            positions = self._screen_positions
            mode = "screen"
        else:
            positions = self._window_positions
            mode = "window"
            
        if not positions:
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
        for p in positions:
            snapshot = {
                "x": p["x"],
                "y": p["y"],
                "delay": p["delay"]
            }
            if mode == "window":
                snapshot["hwnd"] = p["hwnd"]
            positions_snapshot.append(snapshot)
            
        # Hide dots while clicking to avoid blocking
        self._set_dots_visible(False)
        
        self._click_thread = threading.Thread(
            target=self._click_loop, args=(global_interval, positions_snapshot, mode), daemon=True
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
        # Apply to both modes just in case
        for p in self._screen_positions:
            if visible: p["dot"].deiconify()
            else: p["dot"].withdraw()
        for p in self._window_positions:
            if visible: p["dot"].deiconify()
            else: p["dot"].withdraw()

    def _watch_escape(self) -> None:
        while not self._stop_event.wait(0.03):
            if user32.GetAsyncKeyState(VK_ESCAPE) & 0x8000:
                self._stop_event.set()
                break

    def _click_loop(self, global_interval_ms: int, positions: list[dict], mode: str) -> None:
        global_interval_s = global_interval_ms / 1000.0
        while not self._stop_event.is_set():
            for pos in positions:
                if self._stop_event.is_set():
                    break
                
                if mode == "window":
                    hwnd = pos["hwnd"]
                    if user32.IsWindow(hwnd):
                        rect = get_window_rect(hwnd)
                        if rect:
                            # Screen coordinate of the click point
                            sx = rect[0] + pos["x"]
                            sy = rect[1] + pos["y"]
                            
                            # Screen coordinate of client area top-left
                            cl_tl = POINT(0, 0)
                            user32.ClientToScreen(hwnd, ctypes.byref(cl_tl))
                            
                            # Client-relative coordinates
                            cx = int(sx - cl_tl.x)
                            cy = int(sy - cl_tl.y)
                            
                            # Find the actual child window at these client coordinates
                            target_hwnd = user32.ChildWindowFromPointEx(hwnd, POINT(cx, cy), CWP_SKIPINVISIBLE)
                            if not target_hwnd:
                                target_hwnd = hwnd
                                
                            # Convert to target_hwnd's own client coordinates
                            t_cl_tl = POINT(0, 0)
                            user32.ClientToScreen(target_hwnd, ctypes.byref(t_cl_tl))
                            tx = int(sx - t_cl_tl.x)
                            ty = int(sy - t_cl_tl.y)
                            
                            lparam = makelong(tx, ty)
                            user32.PostMessageW(target_hwnd, WM_LBUTTONDOWN, MK_LBUTTON, lparam)
                            user32.PostMessageW(target_hwnd, WM_LBUTTONUP, 0, lparam)
                        else:
                            continue
                    else:
                        continue
                else:
                    self._click_at(pos["x"], pos["y"])

                # Determine wait time: per-step delay or global interval
                delay_ms = pos["delay"] if pos["delay"] is not None else global_interval_ms
                wait_s = delay_ms / 1000.0
                
                if wait_s > 0 and self._stop_event.wait(wait_s):
                    break
            
            # If loop is disabled, stop after one full pass
            if not self.loop_var.get():
                break
                    
        self.root.after(0, self._on_loop_exit)

    def _on_loop_exit(self) -> None:
        self._set_dots_visible(True)
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        self.status_var.set("Stopped")

    def _click_at(self, x: int, y: int) -> None:
        """Move and click using SendInput."""
        send_mouse_click(x, y)

    def export_script(self):
        """Save the current configuration to a JSON file."""
        data = {
            "global_interval": self.interval_var.get(),
            "screen_positions": [
                {"x": p["x"], "y": p["y"], "delay": p["delay"]}
                for p in self._screen_positions
            ],
            "target_windows": [w["title"] for w in self._target_windows],
            "window_positions": [
                {
                    "x": p["x"],
                    "y": p["y"],
                    "delay": p["delay"],
                    "win_title": p["win_title"]
                }
                for p in self._window_positions
            ]
        }
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Export Script"
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
                messagebox.showinfo("Export Successful", f"Script saved to {file_path}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to save script: {e}")

    def import_script(self):
        """Load configuration from a JSON file."""
        file_path = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Import Script"
        )
        if not file_path:
            return
            
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            messagebox.showerror("Import Error", f"Failed to read script: {e}")
            return
            
        # Clear existing
        self.clear_screen_positions()
        self.clear_window_positions()
        self._target_windows.clear()
        
        # Restore global interval
        self.interval_var.set(data.get("global_interval", "500"))
        
        # Restore screen positions
        for p_data in data.get("screen_positions", []):
            idx = len(self._screen_positions)
            dot = DraggableDot(self.root, idx, p_data["x"], p_data["y"], self._on_screen_dot_move,
                              on_click=self._on_screen_dot_click)
            self._screen_positions.append({
                "x": p_data["x"],
                "y": p_data["y"],
                "delay": p_data.get("delay"),
                "dot": dot
            })
        self._refresh_screen_list()
        
        # Restore target windows and re-find HWNDs
        all_active_windows = []
        def enum_callback(hwnd, lparam):
            if user32.IsWindowVisible(hwnd):
                title = get_window_title(hwnd)
                if title:
                    all_active_windows.append((hwnd, title))
            return True
        user32.EnumWindows(EnumWindowsProc(enum_callback), 0)
        
        missing_windows = []
        for win_title in data.get("target_windows", []):
            # Find HWND by title
            found_hwnd = next((h for h, t in all_active_windows if t == win_title), None)
            if found_hwnd:
                self._target_windows.append({"hwnd": found_hwnd, "title": win_title})
            else:
                missing_windows.append(win_title)
        
        self._refresh_window_list()
        
        # Restore window positions
        for p_data in data.get("window_positions", []):
            win_title = p_data["win_title"]
            found_hwnd = next((w["hwnd"] for w in self._target_windows if w["title"] == win_title), None)
            
            # Even if hwnd not found, we keep the data but dot will be hidden/dummy if hwnd is None
            idx = len(self._window_positions)
            dot = DraggableDot(self.root, idx, p_data["x"], p_data["y"], self._on_window_dot_move,
                              on_click=self._on_window_dot_click, hwnd=found_hwnd)
            
            self._window_positions.append({
                "x": p_data["x"],
                "y": p_data["y"],
                "delay": p_data.get("delay"),
                "dot": dot,
                "hwnd": found_hwnd,
                "win_title": win_title
            })
        self._refresh_window_pt_list()
        
        if missing_windows:
            messagebox.showwarning(
                "Missing Windows",
                "The following windows could not be found and their points may not work correctly:\n\n" + 
                "\n".join(missing_windows)
            )
        
        self.status_var.set(f"Imported script from {file_path}")

    def on_close(self) -> None:
        self._stop_event.set()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    ClickerApp().run()
