import ctypes
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from .winapi import (
    user32, kernel32, POINT, RECT, INPUT, MOUSEINPUT, INPUT_MOUSE,
    MOUSEEVENTF_MOVE, MOUSEEVENTF_ABSOLUTE, MOUSEEVENTF_WHEEL,
    SM_CXSCREEN, SM_CYSCREEN, WHEEL_DELTA,
    WM_MOUSEWHEEL, WM_LBUTTONDOWN, WM_LBUTTONUP,
    BUTTON_INPUT_MAP, BUTTON_MESSAGE_MAP,
    CWP_SKIPINVISIBLE, EnumWindowsProc,
    KBDLLHOOKSTRUCT, LowLevelKeyboardProc,
    WH_KEYBOARD_LL, HC_ACTION, LLKHF_EXTENDED, LLKHF_UP,
    makelong, make_wparam, enable_dpi_awareness, sleep_until_deadline,
)
from .hotkey import (
    VK_MAP, DEFAULT_HOTKEYS, HOTKEY_ACTIONS,
    MODIFIER_STATE_BITS, MODIFIER_KEYS,
    is_hotkey_pressed_globally, normalize_hotkey_text, hotkey_from_event,
    modifier_name_from_keysym, key_name_from_event, format_combo,
)
from .script import (
    DOT_SIZE, DEFAULT_AUTO_LOOP_TIMEOUT_SECONDS, DEFAULT_AUTO_LOOP_MAX_ROUNDS,
    DEFAULT_TARGET_WAIT_SECONDS, DEFAULT_INTERVAL_MS, DEFAULT_WAIT_MS,
    DEFAULT_ENABLE_GLOBAL_HOTKEYS,
    POSITION_ACTION_TYPES, MOUSE_BUTTONS, MOUSE_BUTTON_LABELS,
    coerce_non_negative_int, is_position_action, normalize_mouse_action,
    coerce_wheel_delta, get_mouse_action_name, get_mouse_action_details,
    normalize_script_data, read_script_file, write_script_file,
    format_key_combo,
)
from .window import (
    get_window_title, get_window_rect, get_client_rect, client_to_screen,
    get_client_bounds_in_window, clamp_window_position,
    list_visible_windows, find_windows_by_titles,
    perform_screen_mouse_action, perform_window_mouse_action,
    perform_screen_key_action, perform_window_key_action,
)
from .paths import (
    get_app_data_dir, get_auto_config_path, get_auto_log_path,
    write_auto_log, show_already_running_message,
)

class DraggableDot(tk.Toplevel):
    """A semi-transparent, numbered, draggable dot that stays on top."""
    def __init__(self, master, index, x, y, on_move, on_click=None, hwnd=None, action_type="click"):
        super().__init__(master)
        self.index = index  # 0-based index
        self.on_move = on_move
        self.on_click = on_click
        self.hwnd = hwnd # If set, x and y are relative to this window's top-left
        self.action_type = action_type

        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.75)

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

        # Determine colors based on action type
        if action_type == "wheel":
            halo_color = "#f1cbe9"  # Light Purple
            dot_color = "#b4009e"   # Purple/Magenta
        else:
            halo_color = "#c7e0f4"  # Light Blue
            dot_color = "#0078d7"   # Primary Blue

        # 1. Outer halo border
        self.halo = self.canvas.create_oval(2, 2, DOT_SIZE-2, DOT_SIZE-2, fill=halo_color, outline="")

        # 2. Main Dot
        inner_m = 6
        self.circle = self.canvas.create_oval(inner_m, inner_m, DOT_SIZE-inner_m, DOT_SIZE-inner_m, fill=dot_color, outline="white", width=1)

        # 3. Sequence Number (Modern Segoe UI font)
        self.text = self.canvas.create_text(DOT_SIZE//2, DOT_SIZE//2, text=str(index+1), fill="white", font=("Segoe UI", 9, "bold"))

        # 4. Glossy 3D Highlight Reflection
        self.highlight = self.canvas.create_oval(11, 11, 17, 15, fill="white", outline="")

        self.canvas.bind("<Button-1>", self._on_start)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<Enter>", self._on_enter)
        self.canvas.bind("<Leave>", self._on_leave)

    def _on_enter(self, event):
        if self.action_type == "wheel":
            self.canvas.itemconfig(self.halo, fill="#e2b1d6") # richer purple halo
            self.canvas.itemconfig(self.circle, fill="#881794") # richer active purple
        else:
            self.canvas.itemconfig(self.halo, fill="#a9d1f5") # richer blue halo
            self.canvas.itemconfig(self.circle, fill="#106ebe") # richer active blue

    def _on_leave(self, event):
        if self.action_type == "wheel":
            self.canvas.itemconfig(self.halo, fill="#f1cbe9")
            self.canvas.itemconfig(self.circle, fill="#b4009e")
        else:
            self.canvas.itemconfig(self.halo, fill="#c7e0f4")
            self.canvas.itemconfig(self.circle, fill="#0078d7")
        
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
                rel_x = new_screen_x - rect[0]
                rel_y = new_screen_y - rect[1]
                rel_x, rel_y = clamp_window_position(self.hwnd, rel_x, rel_y)
                new_screen_x = rect[0] + rel_x
                new_screen_y = rect[1] + rel_y
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
        self.root.resizable(True, True)
        # Provisional minsize — the real value is computed once the layout
        # has settled (see _compute_root_minsize). Floor stays at 680x520 so
        # the first paint isn't a sliver.
        self.root.minsize(680, 520)

        self.interval_var = tk.StringVar(value=str(DEFAULT_INTERVAL_MS))
        self.default_wait_var = tk.StringVar(value=str(DEFAULT_WAIT_MS))
        self.step_delay_var = tk.StringVar()
        self.custom_delay_var = tk.StringVar()
        self.mouse_button_var = tk.StringVar(value="left")
        self.loop_var = tk.BooleanVar(value=True)
        self.enable_global_hotkeys_var = tk.BooleanVar(value=DEFAULT_ENABLE_GLOBAL_HOTKEYS)
        self.status_var = tk.StringVar(value="Ready")
        self.auto_loop_timeout_var = tk.StringVar(value=str(DEFAULT_AUTO_LOOP_TIMEOUT_SECONDS))
        self.auto_loop_max_rounds_var = tk.StringVar(value=str(DEFAULT_AUTO_LOOP_MAX_ROUNDS))
        self._active_mode = "screen"
        self._button_controls: list[tk.Widget] = []
        
        self.hotkey_vars = {
            action: tk.StringVar(value=default)
            for action, default in DEFAULT_HOTKEYS.items()
        }
        self._hotkey_map: dict[str, str] = {}
        # Screen Mode State
        self._screen_positions: list[dict] = []
        
        # Window Mode State
        self._window_positions: list[dict] = []
        self._target_windows: list[dict] = [] # {"hwnd": int, "title": str}
        
        self._stop_event = threading.Event()
        self._click_thread: threading.Thread | None = None
        self._escape_thread: threading.Thread | None = None

        # Key-capture state (active while a Key action's entry has focus)
        self._capturing_key = False
        self._key_capture_index: int | None = None
        self._key_capture_mode: str = "screen"
        self._key_pressed_keycodes: set[int] = set()
        self._key_combo_modifiers: list[str] = []
        self._key_combo_main: str | None = None
        self._key_combo_main_scan: int = 0
        self._key_combo_main_extended: bool = False
        self._key_combo_mod_scans: dict[str, int] = {}
        self._kb_hook = None

        self._build_ui()
        self._apply_hotkeys(show_status=False)
        self.sync_dots_loop()
        self.root.bind_all("<KeyPress>", self._on_key_press, add="+")
        
        self._hotkey_thread = threading.Thread(target=self._watch_global_hotkeys, daemon=True)
        self._hotkey_thread.start()
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _apply_ui_theme(self) -> None:
        style = ttk.Style()
        if "clam" in style.theme_names():
            style.theme_use("clam")
            
        bg_main = "#f3f2f1"
        bg_card = "#ffffff"
        fg_text = "#323130"
        primary = "#0078d7"
        primary_hover = "#106ebe"
        primary_light = "#deecf9"
        border_color = "#d2d0ce"
        
        style.configure(".", background=bg_main, foreground=fg_text, font=("Segoe UI", 9))
        style.configure("TFrame", background=bg_main)
        style.configure("TLabelframe", background=bg_main, bordercolor=border_color, borderwidth=1)
        style.configure("TLabelframe.Label", background=bg_main, foreground="#605e5c", font=("Segoe UI", 9, "bold"))
        
        style.configure("TButton", padding=(8, 4), background=bg_card, bordercolor=border_color, focuscolor="", relief="flat")
        style.map("TButton",
            background=[("active", primary_light), ("disabled", "#f3f2f1")],
            foreground=[("active", primary), ("disabled", "#a19f9d")],
            bordercolor=[("active", primary)]
        )
        
        style.configure("Accent.TButton", padding=(8, 4), background=primary, foreground="#ffffff", bordercolor=primary, focuscolor="", relief="flat")
        style.map("Accent.TButton",
            background=[("active", primary_hover), ("disabled", "#f3f2f1")],
            foreground=[("active", "#ffffff"), ("disabled", "#a19f9d")],
            bordercolor=[("active", primary_hover)]
        )
        
        style.configure("TEntry", padding=4, insertcolor=fg_text, bordercolor=border_color, fieldbackground=bg_card)
        style.map("TEntry",
            bordercolor=[("focus", primary), ("hover", "#8a8886")]
        )
        
        style.configure("TCheckbutton", background=bg_main, focuscolor="")
        style.configure("TCombobox", padding=4, arrowsize=12, bordercolor=border_color, fieldbackground=bg_card)
        style.map("TCombobox",
            bordercolor=[("focus", primary), ("hover", "#8a8886")]
        )
        
        style.configure("TNotebook", background=bg_main, bordercolor=border_color, borderwidth=1)
        style.configure("TNotebook.Tab", background="#e1dfdd", padding=(12, 6), bordercolor=border_color, lightcolor="#e1dfdd")
        style.map("TNotebook.Tab",
            background=[("selected", bg_card), ("active", "#deecf9")],
            lightcolor=[("selected", bg_card)],
            bordercolor=[("selected", border_color)]
        )

    def _build_ui(self) -> None:
        self._apply_ui_theme()

        # Global Run controls and Status — packed FIRST at the bottom so
        # they survive when the user shrinks the window. The notebook above
        # is the only widget that gets clipped.
        bottom_frame = ttk.Frame(self.root, padding=(8, 0, 8, 8))
        bottom_frame.pack(side="bottom", fill="x")
        bottom_frame.columnconfigure(1, weight=1)

        run_frame = ttk.Frame(bottom_frame)
        run_frame.grid(row=0, column=0, sticky="w")
        ttk.Label(run_frame, text="Interval").pack(side="left")
        ttk.Entry(run_frame, textvariable=self.interval_var, width=8).pack(side="left", padx=(4, 8))
        ttk.Checkbutton(run_frame, text="Loop", variable=self.loop_var).pack(side="left", padx=(0, 8))
        self.start_button = ttk.Button(run_frame, text="Start", command=self.start_clicking, width=8, style="Accent.TButton")
        self.start_button.pack(side="left", padx=(0, 4))
        self.stop_button = ttk.Button(run_frame, text="Stop", command=self.stop_clicking, state="disabled", width=8)
        self.stop_button.pack(side="left")

        script_frame = ttk.Frame(bottom_frame)
        script_frame.grid(row=0, column=2, sticky="e")
        ttk.Button(script_frame, text="Import", command=self.import_script).pack(side="left", padx=(0, 4))
        ttk.Button(script_frame, text="Export", command=self.export_script).pack(side="left", padx=(0, 4))
        ttk.Button(script_frame, text="Auto Config", command=self.open_auto_config_dialog).pack(side="left")

        ttk.Label(bottom_frame, textvariable=self.status_var, foreground="#005a9e", font=("", 9, "bold")).grid(
            row=1, column=0, columnspan=3, sticky="w", pady=(6, 0)
        )

        # Notebook for tabs (packed AFTER bottom_frame so it lives above and
        # is the first widget the geometry manager clips when shrinking).
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(side="top", fill="both", expand=True)

        # Screen Mode Tab
        self.screen_frame = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(self.screen_frame, text="Screen Mode")
        self._build_screen_mode_ui(self.screen_frame)

        # Window Mode Tab
        self.window_frame = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(self.window_frame, text="Window Mode")
        self._build_window_mode_ui(self.window_frame)

        self.settings_frame = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(self.settings_frame, text="Settings")
        self._build_settings_ui(self.settings_frame)

        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

    def _build_settings_ui(self, frame) -> None:
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        # Wrap everything in a scrollable canvas so content never clips.
        canvas = tk.Canvas(frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Make scrollable_frame expand to fill canvas width
        def _on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)
        canvas.bind("<Configure>", _on_canvas_configure)

        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        # Bind mousewheel to canvas for smooth scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        scrollable_frame.columnconfigure(0, weight=1)

        info = ttk.LabelFrame(scrollable_frame, text="Window Mode", padding=10)
        info.grid(row=0, column=0, sticky="ew")
        ttk.Label(info, text="Window Mode is client-area only in the minified build.").grid(row=0, column=0, sticky="w")
        ttk.Label(
            info,
            text="Title bars, minimize, maximize, and close buttons are intentionally unsupported to keep clicks pure background and dependency-free.",
            foreground="#555555",
            wraplength=500,
        ).grid(row=1, column=0, sticky="ew", pady=(4, 0))

        hotkey_scope_frame = ttk.LabelFrame(scrollable_frame, text="Hotkey Scope", padding=10)
        hotkey_scope_frame.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        ttk.Checkbutton(
            hotkey_scope_frame,
            text="Enable global hotkeys",
            variable=self.enable_global_hotkeys_var,
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            hotkey_scope_frame,
            text="When enabled, shortcuts trigger system-wide (works without focusing ClickTool). When disabled, shortcuts only fire when ClickTool has focus.",
            foreground="#555555",
            wraplength=500,
        ).grid(row=1, column=0, sticky="ew", pady=(4, 0))

        defaults_frame = ttk.LabelFrame(scrollable_frame, text="Defaults", padding=10)
        defaults_frame.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        defaults_frame.columnconfigure(1, weight=1)
        ttk.Label(defaults_frame, text="Interval (ms)").grid(row=0, column=0, sticky="w")
        ttk.Entry(defaults_frame, textvariable=self.interval_var, width=10).grid(row=0, column=1, sticky="w", padx=(8, 18))
        ttk.Label(defaults_frame, text="Wait item (ms)").grid(row=0, column=2, sticky="w")
        ttk.Entry(defaults_frame, textvariable=self.default_wait_var, width=10).grid(row=0, column=3, sticky="w", padx=(8, 0))
        ttk.Button(defaults_frame, text="Apply", command=self.apply_defaults).grid(row=0, column=4, sticky="e", padx=(16, 0))

        hotkey_frame = ttk.LabelFrame(scrollable_frame, text="Shortcuts", padding=10)
        hotkey_frame.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        for col in (1, 3):
            hotkey_frame.columnconfigure(col, weight=1)

        for index, (action, label) in enumerate(HOTKEY_ACTIONS):
            row = index // 2
            col = (index % 2) * 2
            ttk.Label(hotkey_frame, text=label).grid(row=row, column=col, sticky="w", pady=2, padx=(0, 6))
            ttk.Entry(hotkey_frame, textvariable=self.hotkey_vars[action], width=18).grid(
                row=row,
                column=col + 1,
                sticky="ew",
                pady=2,
                padx=(0, 14 if col == 0 else 0),
            )

        ttk.Button(hotkey_frame, text="Apply Shortcuts", command=self._apply_hotkeys).grid(
            row=(len(HOTKEY_ACTIONS) + 1) // 2,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(8, 0),
        )
        ttk.Button(hotkey_frame, text="Reset", command=self.reset_hotkeys).grid(
            row=(len(HOTKEY_ACTIONS) + 1) // 2,
            column=2,
            sticky="w",
            pady=(8, 0),
        )
        ttk.Label(
            hotkey_frame,
            text="Examples: Ctrl+D, Ctrl+Shift+W, Esc. Leave blank to disable an action.",
            foreground="#555555",
        ).grid(row=((len(HOTKEY_ACTIONS) + 1) // 2) + 1, column=0, columnspan=4, sticky="w", pady=(6, 0))

    def _build_screen_mode_ui(self, frame) -> None:
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(2, weight=1)
        # Row 1: Position List Label
        ttk.Label(frame, text="Click Order & Positions").grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(0, 4)
        )

        # Row 2: Listbox
        list_frame = ttk.Frame(frame)
        list_frame.grid(row=2, column=0, columnspan=2, sticky="nsew")
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        self.screen_list = tk.Listbox(
            list_frame,
            height=9,
            width=56,
            activestyle="dotbox",
            bg="white",
            fg="#323130",
            selectbackground="#deecf9",
            selectforeground="#0078d7",
            font=("Segoe UI", 9),
            borderwidth=1,
            relief="flat",
            highlightthickness=1,
            highlightbackground="#d2d0ce",
            highlightcolor="#0078d7"
        )
        self.screen_list.grid(row=0, column=0, sticky="nsew")
        self.screen_list.bind("<<ListboxSelect>>", self._on_screen_list_select)

        scrollbar = ttk.Scrollbar(
            list_frame, orient="vertical", command=self.screen_list.yview
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.screen_list.config(yscrollcommand=scrollbar.set)

        # Row 3: Selected Item Properties
        prop_frame = ttk.LabelFrame(frame, text="Selected Item Properties", padding=8)
        prop_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        prop_frame.columnconfigure(3, weight=1)

        self.screen_prop_label = ttk.Label(prop_frame, text="Value:")
        self.screen_prop_label.grid(row=0, column=0, sticky="w")
        self.screen_step_delay_entry = ttk.Entry(prop_frame, textvariable=self.step_delay_var, width=15)
        self.screen_step_delay_entry.grid(row=0, column=1, padx=4)
        ttk.Button(prop_frame, text="Apply", command=self.apply_step_delay).grid(row=0, column=2)

        ttk.Label(prop_frame, text="Button:").grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.screen_button_combo = ttk.Combobox(
            prop_frame,
            textvariable=self.mouse_button_var,
            values=MOUSE_BUTTONS,
            state="readonly",
            width=12,
        )
        self.screen_button_combo.grid(row=1, column=1, sticky="w", padx=4, pady=(6, 0))
        self.screen_button_combo.bind("<<ComboboxSelected>>", self._on_mouse_button_selected)
        self._button_controls.append(self.screen_button_combo)

        ttk.Label(prop_frame, text="Custom Delay (ms):").grid(row=1, column=2, sticky="w", pady=(6, 0), padx=(10, 0))
        self.screen_custom_delay_entry = ttk.Entry(prop_frame, textvariable=self.custom_delay_var, width=12)
        self.screen_custom_delay_entry.grid(row=1, column=3, sticky="w", pady=(6, 0))

        ttk.Label(
            prop_frame,
            text="Click: x,y + button; Wheel: x,y,delta; Wait: ms",
            font=("", 8),
            foreground="#666666",
        ).grid(row=2, column=0, columnspan=4, sticky="w")

        # Row 4: Controls
        edit_row = ttk.Frame(frame)
        edit_row.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        add_group = ttk.LabelFrame(edit_row, text="Add", padding=(6, 4))
        add_group.pack(side="left", padx=(0, 8))
        ttk.Button(add_group, text="Dot", command=self.add_screen_dot, width=9).pack(side="left", padx=(0, 4))
        ttk.Button(add_group, text="Wheel", command=self.add_screen_wheel, width=9).pack(side="left", padx=(0, 4))
        ttk.Button(add_group, text="Key", command=self.add_screen_key, width=9).pack(side="left", padx=(0, 4))
        ttk.Button(add_group, text="Wait", command=self.add_screen_wait, width=9).pack(side="left")

        edit_group = ttk.LabelFrame(edit_row, text="Edit", padding=(6, 4))
        edit_group.pack(side="left")
        ttk.Button(edit_group, text="Remove", command=self.remove_screen_position, width=9).pack(side="left", padx=(0, 4))
        ttk.Button(edit_group, text="Up", width=5, command=lambda: self.move_screen_position(-1)).pack(side="left", padx=(0, 4))
        ttk.Button(edit_group, text="Down", width=6, command=lambda: self.move_screen_position(1)).pack(side="left", padx=(0, 4))
        ttk.Button(edit_group, text="Clear", command=self.clear_screen_positions, width=8).pack(side="left")

    def _build_window_mode_ui(self, frame) -> None:
        # Two columns: Window Column and Click Point Column
        paned = ttk.PanedWindow(frame, orient="horizontal")
        paned.grid(row=0, column=0, sticky="nsew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        self._win_paned = paned
        self._win_pane_min_left = 180
        self._win_pane_min_right = 380
        paned.bind("<B1-Motion>", self._clamp_paned_sash)
        paned.bind("<ButtonRelease-1>", self._clamp_paned_sash)
        paned.bind("<Configure>", self._clamp_paned_sash)

        # Left: Window Column
        win_frame = ttk.Frame(paned, padding=(0, 0, 8, 0))
        paned.add(win_frame, weight=1)
        try:
            paned.paneconfigure(win_frame, minsize=self._win_pane_min_left)
        except tk.TclError:
            pass

        ttk.Label(win_frame, text="Target Windows").pack(anchor="w")

        win_list_frame = ttk.Frame(win_frame)
        win_list_frame.pack(fill="both", expand=True, pady=4)

        self.target_win_list = tk.Listbox(
            win_list_frame,
            height=12,
            width=28,
            bg="white",
            fg="#323130",
            selectbackground="#deecf9",
            selectforeground="#0078d7",
            font=("Segoe UI", 9),
            borderwidth=1,
            relief="flat",
            highlightthickness=1,
            highlightbackground="#d2d0ce",
            highlightcolor="#0078d7"
        )
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
        try:
            paned.paneconfigure(pt_frame, minsize=self._win_pane_min_right)
        except tk.TclError:
            pass
        
        ttk.Label(pt_frame, text="Click Points (Cross-window sorting allowed)").pack(anchor="w")
        
        pt_list_frame = ttk.Frame(pt_frame)
        pt_list_frame.pack(fill="both", expand=True, pady=4)
        
        self.window_pt_list = tk.Listbox(
            pt_list_frame,
            height=12,
            width=44,
            bg="white",
            fg="#323130",
            selectbackground="#deecf9",
            selectforeground="#0078d7",
            font=("Segoe UI", 9),
            borderwidth=1,
            relief="flat",
            highlightthickness=1,
            highlightbackground="#d2d0ce",
            highlightcolor="#0078d7"
        )
        self.window_pt_list.pack(side="left", fill="both", expand=True)
        self.window_pt_list.bind("<<ListboxSelect>>", self._on_window_list_select)
        
        pt_scroll = ttk.Scrollbar(pt_list_frame, orient="vertical", command=self.window_pt_list.yview)
        pt_scroll.pack(side="right", fill="y")
        self.window_pt_list.config(yscrollcommand=pt_scroll.set)
        
        pt_btn_row = ttk.Frame(pt_frame)
        pt_btn_row.pack(fill="x")
        add_group = ttk.LabelFrame(pt_btn_row, text="Add", padding=(6, 4))
        add_group.pack(side="left", padx=(0, 8))
        ttk.Button(add_group, text="Dot", command=self.add_window_dot, width=9).pack(side="left", padx=(0, 4))
        ttk.Button(add_group, text="Wheel", command=self.add_window_wheel, width=9).pack(side="left", padx=(0, 4))
        ttk.Button(add_group, text="Key", command=self.add_window_key, width=9).pack(side="left", padx=(0, 4))
        ttk.Button(add_group, text="Wait", command=self.add_window_wait, width=9).pack(side="left")

        edit_group = ttk.LabelFrame(pt_btn_row, text="Edit", padding=(6, 4))
        edit_group.pack(side="left")
        ttk.Button(edit_group, text="Remove", command=self.remove_window_position, width=9).pack(side="left", padx=(0, 4))
        ttk.Button(edit_group, text="Up", width=5, command=lambda: self.move_window_position(-1)).pack(side="left", padx=(0, 4))
        ttk.Button(edit_group, text="Down", width=6, command=lambda: self.move_window_position(1)).pack(side="left", padx=(0, 4))
        ttk.Button(edit_group, text="Clear", command=self.clear_window_positions, width=8).pack(side="left")

        # Selected Item Properties for Window Mode
        win_prop_frame = ttk.LabelFrame(pt_frame, text="Selected Item Properties", padding=8)
        win_prop_frame.pack(fill="x", pady=(8, 0))
        win_prop_frame.columnconfigure(3, weight=1)

        self.window_prop_label = ttk.Label(win_prop_frame, text="Value:")
        self.window_prop_label.grid(row=0, column=0, sticky="w")
        self.window_step_delay_entry = ttk.Entry(win_prop_frame, textvariable=self.step_delay_var, width=15)
        self.window_step_delay_entry.grid(row=0, column=1, padx=4)
        ttk.Button(win_prop_frame, text="Apply", command=self.apply_step_delay).grid(row=0, column=2)

        ttk.Label(win_prop_frame, text="Button:").grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.window_button_combo = ttk.Combobox(
            win_prop_frame,
            textvariable=self.mouse_button_var,
            values=MOUSE_BUTTONS,
            state="readonly",
            width=12,
        )
        self.window_button_combo.grid(row=1, column=1, sticky="w", padx=4, pady=(6, 0))
        self.window_button_combo.bind("<<ComboboxSelected>>", self._on_mouse_button_selected)
        self._button_controls.append(self.window_button_combo)

        ttk.Label(win_prop_frame, text="Custom Delay (ms):").grid(row=1, column=2, sticky="w", pady=(6, 0), padx=(10, 0))
        self.window_custom_delay_entry = ttk.Entry(win_prop_frame, textvariable=self.custom_delay_var, width=12)
        self.window_custom_delay_entry.grid(row=1, column=3, sticky="w", pady=(6, 0))

        ttk.Label(
            win_prop_frame,
            text="Click: x,y + button; Wheel: x,y,delta; Wait: ms",
            font=("", 8),
            foreground="#666666",
        ).grid(row=2, column=0, columnspan=4, sticky="w")

    def _on_tab_changed(self, event):
        """Show only the dots belonging to the active tab."""
        # If clicking is active, dots are already hidden
        if self._click_thread and self._click_thread.is_alive():
            return

        current_tab = self.notebook.index(self.notebook.select())
        if current_tab == 0: # Screen
            self._active_mode = "screen"
            for p in self._screen_positions:
                if is_position_action(p) and "dot" in p: p["dot"].deiconify()
            for p in self._window_positions:
                if is_position_action(p) and "dot" in p: p["dot"].withdraw()
        elif current_tab == 1: # Window
            self._active_mode = "window"
            for p in self._screen_positions:
                if is_position_action(p) and "dot" in p: p["dot"].withdraw()
            for p in self._window_positions:
                if is_position_action(p) and "dot" in p: p["dot"].deiconify()
        else: # Settings -- keep the last edited mode's dots visible so users
              # can see coordinate effects while tweaking shortcuts or defaults
            if self._active_mode == "screen":
                for p in self._screen_positions:
                    if is_position_action(p) and "dot" in p: p["dot"].deiconify()
                for p in self._window_positions:
                    if is_position_action(p) and "dot" in p: p["dot"].withdraw()
            else:
                for p in self._screen_positions:
                    if is_position_action(p) and "dot" in p: p["dot"].withdraw()
                for p in self._window_positions:
                    if is_position_action(p) and "dot" in p: p["dot"].deiconify()

    def _clamp_paned_sash(self, event=None) -> None:
        """Prevent the Window Mode sash from being dragged so far that either
        pane becomes unusable."""
        paned = getattr(self, "_win_paned", None)
        if paned is None:
            return
        try:
            total = paned.winfo_width()
            if total <= 1:
                return
            current = paned.sashpos(0)
            min_left = self._win_pane_min_left
            max_left = max(min_left, total - self._win_pane_min_right)
            clamped = max(min_left, min(current, max_left))
            if clamped != current:
                paned.sashpos(0, clamped)
        except (tk.TclError, AttributeError):
            pass

    def _compute_root_minsize(self) -> None:
        """Lock the root window's minimum size to the smallest layout that
        still fits every tab."""
        try:
            self.root.update_idletasks()

            min_h = 0
            for tab_id in self.notebook.tabs():
                tab_widget = self.notebook.nametowidget(tab_id)
                min_h = max(min_h, int(tab_widget.winfo_reqheight()))
            # Notebook tab strip + bottom bar + a little chrome.
            tab_strip = 32
            bottom = 0
            for child in self.root.winfo_children():
                if child is self.notebook:
                    continue
                bottom += int(child.winfo_reqheight())
            min_h += tab_strip + bottom + 16

            min_w = max(680, int(self.notebook.winfo_reqwidth()) + 32)
            self.root.minsize(min_w, min_h)
        except (tk.TclError, AttributeError):
            pass
        paned = getattr(self, "_win_paned", None)
        if paned is None:
            return
        try:
            total = paned.winfo_width()
            if total <= 1:
                return
            current = paned.sashpos(0)
            min_left = self._win_pane_min_left
            max_left = max(min_left, total - self._win_pane_min_right)
            clamped = max(min_left, min(current, max_left))
            if clamped != current:
                paned.sashpos(0, clamped)
        except (tk.TclError, AttributeError):
            pass

    def sync_dots_loop(self):
        """Update window-based dots to follow their windows and prevent overflow."""
        # Only sync if we are not clicking
        is_clicking = self._click_thread and self._click_thread.is_alive()
        current_tab = self.notebook.index(self.notebook.select())
        
        if current_tab == 1 and not is_clicking:
            active_windows = None
            for w in self._target_windows:
                hwnd = w["hwnd"]
                if not hwnd or not user32.IsWindow(hwnd):
                    if active_windows is None:
                        active_windows = list_visible_windows()
                    found_hwnd = next((h for h, t in active_windows if t == w["title"]), None)
                    if not found_hwnd:
                        found_hwnd = next((h for h, t in active_windows if w["title"].lower() in t.lower()), None)
                    if found_hwnd:
                        w["hwnd"] = found_hwnd
                        for p in self._window_positions:
                            if p.get("win_title") == w["title"]:
                                p["hwnd"] = found_hwnd
                                if "dot" in p:
                                    p["dot"].hwnd = found_hwnd

            for p in self._window_positions:
                if not is_position_action(p) or "dot" not in p:
                    continue
                hwnd = p.get("hwnd")
                if hwnd and user32.IsWindow(hwnd):
                    if user32.IsIconic(hwnd):
                        p["dot"].withdraw()
                    else:
                        rect = get_window_rect(hwnd)
                        if rect:
                            display_x, display_y = clamp_window_position(hwnd, p["x"], p["y"])
                            sx = rect[0] + display_x
                            sy = rect[1] + display_y
                            p["dot"].deiconify()
                            p["dot"].update_position(sx, sy)
                        else:
                            p["dot"].withdraw()
                else:
                    p["dot"].withdraw()

        self.root.after(200, self.sync_dots_loop)

    def add_target_window(self):
        """Open a dialog to select a window from all visible windows."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Select Window (Auto-refreshing)")
        dialog.geometry("480x520")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 1. Drag & Drop Targeting Tool Frame
        drag_frame = ttk.LabelFrame(dialog, text="Drag & Drop Targeting Tool", padding=10)
        drag_frame.pack(fill="x", padx=10, pady=(8, 4))
        
        info_label = ttk.Label(drag_frame, text="Drag the target icon onto any window to add it automatically:", foreground="#555555")
        info_label.pack(anchor="w", pady=(0, 6))
        
        tool_row = ttk.Frame(drag_frame)
        tool_row.pack(fill="x")
        
        target_canvas = tk.Canvas(tool_row, width=44, height=44, bg="#deecf9", highlightthickness=1, highlightbackground="#0078d7", cursor="crosshair")
        target_canvas.pack(side="left", padx=(0, 10))
        
        # Draw target icon inside target_canvas
        target_canvas.create_oval(10, 10, 34, 34, outline="#0078d7", width=2)
        target_canvas.create_oval(18, 18, 26, 26, fill="#0078d7", outline="")
        target_canvas.create_line(4, 22, 40, 22, fill="#0078d7", width=2)
        target_canvas.create_line(22, 4, 22, 40, fill="#0078d7", width=2)
        
        status_var = tk.StringVar(value="Hold & drag the crosshair target...")
        status_label = ttk.Label(tool_row, textvariable=status_var, font=("Segoe UI", 9, "bold"), foreground="#0078d7", wraplength=350)
        status_label.pack(side="left", fill="both", expand=True)
        
        drag_hwnd = None
        drag_title = ""
        
        def on_drag_start(event):
            nonlocal drag_hwnd, drag_title
            drag_hwnd = None
            drag_title = ""
            status_var.set("Dragging... Hover over any window.")
            status_label.config(foreground="#106ebe")
            
        def on_drag_motion(event):
            nonlocal drag_hwnd, drag_title
            try:
                pt = POINT()
                if user32.GetCursorPos(ctypes.byref(pt)):
                    hwnd = user32.WindowFromPoint(pt)
                    hwnd = user32.GetAncestor(hwnd, 2) # GA_ROOT
                    
                    dialog_hwnd = int(dialog.winfo_id())
                    main_hwnd = int(self.root.winfo_id())
                    
                    is_our_win = False
                    curr = hwnd
                    while curr:
                        if curr == dialog_hwnd or curr == main_hwnd:
                            is_our_win = True
                            break
                        curr = user32.GetParent(curr)
                    
                    if is_our_win:
                        status_var.set("Cannot select ClickTool window itself!")
                        drag_hwnd = None
                        drag_title = ""
                    else:
                        title = get_window_title(hwnd)
                        if title:
                            drag_hwnd = hwnd
                            drag_title = title
                            status_var.set(f"Target: '{title}'")
                        else:
                            status_var.set("Hovering unnamed window...")
                            drag_hwnd = None
                            drag_title = ""
            except Exception as e:
                status_var.set(f"Error: {e}")
                
        def on_drag_release(event):
            nonlocal drag_hwnd, drag_title
            status_label.config(foreground="#0078d7")
            if drag_hwnd and drag_title:
                hwnd = drag_hwnd
                title = drag_title
                if any(w["hwnd"] == hwnd for w in self._target_windows):
                    messagebox.showinfo("Already Added", f"Window '{title}' is already in your target list.")
                else:
                    self._target_windows.append({"hwnd": hwnd, "title": title})
                    self._refresh_window_list()
                    new_idx = len(self._target_windows) - 1
                    self.target_win_list.selection_clear(0, "end")
                    self.target_win_list.selection_set(new_idx)
                    self.target_win_list.activate(new_idx)
                    dialog.destroy()
            else:
                status_var.set("Hold & drag the crosshair target...")
                
        target_canvas.bind("<Button-1>", on_drag_start)
        target_canvas.bind("<B1-Motion>", on_drag_motion)
        target_canvas.bind("<ButtonRelease-1>", on_drag_release)
        
        # 2. List Selection Frame
        ttk.Label(dialog, text="Or select a window from the list:").pack(anchor="w", padx=10, pady=(8, 4))
        
        list_frame = ttk.Frame(dialog)
        list_frame.pack(fill="both", expand=True, padx=10)
        
        lb = tk.Listbox(
            list_frame,
            bg="white",
            fg="#323130",
            selectbackground="#deecf9",
            selectforeground="#0078d7",
            font=("Segoe UI", 9),
            borderwidth=1,
            relief="flat",
            highlightthickness=1,
            highlightbackground="#d2d0ce",
            highlightcolor="#0078d7"
        )
        lb.pack(side="left", fill="both", expand=True)
        
        scroll = ttk.Scrollbar(list_frame, orient="vertical", command=lb.yview)
        scroll.pack(side="right", fill="y")
        lb.config(yscrollcommand=scroll.set)
        
        current_windows = []
        scan_buffer: list[tuple[int, str]] = []

        def enum_callback(hwnd, lparam):
            if user32.IsWindowVisible(hwnd):
                title = get_window_title(hwnd)
                if title:
                    scan_buffer.append((hwnd, title))
            return True

        enum_proc = EnumWindowsProc(enum_callback)

        def refresh_list():
            if not dialog.winfo_exists():
                return

            nonlocal current_windows
            scan_buffer.clear()
            user32.EnumWindows(enum_proc, 0)
            new_windows = sorted(scan_buffer, key=lambda x: x[1].lower())

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
                if any(w["hwnd"] == hwnd for w in self._target_windows):
                    messagebox.showinfo("Already Added", "This window is already in your target list.")
                else:
                    self._target_windows.append({"hwnd": hwnd, "title": title})
                    self._refresh_window_list()
                    new_idx = len(self._target_windows) - 1
                    self.target_win_list.selection_clear(0, "end")
                    self.target_win_list.selection_set(new_idx)
                    self.target_win_list.activate(new_idx)
                dialog.destroy()
        
        button_row = ttk.Frame(dialog)
        button_row.pack(fill="x", padx=10, pady=8)
        ttk.Button(button_row, text="Select", command=on_select).pack(side="right")
        ttk.Button(button_row, text="Cancel", command=dialog.destroy).pack(side="right", padx=(0, 6))

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
            if is_position_action(self._window_positions[i]) and "dot" in self._window_positions[i]:
                self._window_positions[i]["dot"].destroy()
            del self._window_positions[i]

        del self._target_windows[index]
        self._refresh_window_list()
        self._refresh_window_pt_list()

    def _set_button_controls_enabled(self, enabled: bool) -> None:
        state = "readonly" if enabled else "disabled"
        for control in self._button_controls:
            try:
                control.config(state=state)
            except tk.TclError:
                pass

    def _on_mouse_button_selected(self, event=None) -> None:
        current_tab = self.notebook.index(self.notebook.select())
        editing_screen = current_tab == 0 or (current_tab == 2 and self._active_mode == "screen")
        listbox = self.screen_list if editing_screen else self.window_pt_list
        positions = self._screen_positions if editing_screen else self._window_positions
        sel = listbox.curselection()
        if not sel:
            return

        index = sel[0]
        if positions[index].get("type") != "click":
            return

        button = self.mouse_button_var.get()
        positions[index]["button"] = button if button in MOUSE_BUTTONS else "left"
        if editing_screen:
            self._refresh_screen_list()
            self.screen_list.selection_set(index)
        else:
            self._refresh_window_pt_list()
            self.window_pt_list.selection_set(index)

    def add_screen_dot(self, at_cursor: bool = False) -> None:
        """Create a new draggable dot at the cursor or screen center."""
        x, y = None, None
        if at_cursor:
            try:
                pt = POINT()
                if user32.GetCursorPos(ctypes.byref(pt)):
                    x, y = pt.x, pt.y
            except Exception:
                pass
        if x is None or y is None:
            screen_w = user32.GetSystemMetrics(SM_CXSCREEN)
            screen_h = user32.GetSystemMetrics(SM_CYSCREEN)
            x, y = screen_w // 2, screen_h // 2

        index = len(self._screen_positions)
        dot = DraggableDot(self.root, index, x, y, self._on_screen_dot_move,
                          on_click=self._on_screen_dot_click, action_type="click")

        self._screen_positions.append({
            "type": "click",
            "x": x,
            "y": y,
            "button": "left",
            "delay": None,
            "dot": dot
        })
        self._refresh_screen_list()
        last_idx = len(self._screen_positions) - 1
        self.screen_list.selection_clear(0, "end")
        self.screen_list.selection_set(last_idx)
        self.screen_list.activate(last_idx)
        self._on_screen_list_select()
        self.status_var.set(f"Added screen dot at ({x}, {y}).")

    def add_screen_wheel(self, at_cursor: bool = False) -> None:
        """Create a wheel action at the cursor or screen center."""
        x, y = None, None
        if at_cursor:
            try:
                pt = POINT()
                if user32.GetCursorPos(ctypes.byref(pt)):
                    x, y = pt.x, pt.y
            except Exception:
                pass
        if x is None or y is None:
            screen_w = user32.GetSystemMetrics(SM_CXSCREEN)
            screen_h = user32.GetSystemMetrics(SM_CYSCREEN)
            x, y = screen_w // 2, screen_h // 2

        index = len(self._screen_positions)
        dot = DraggableDot(self.root, index, x, y, self._on_screen_dot_move,
                          on_click=self._on_screen_dot_click, action_type="wheel")

        self._screen_positions.append({
            "type": "wheel",
            "x": x,
            "y": y,
            "delta": -1,
            "delay": None,
            "dot": dot
        })
        self._refresh_screen_list()
        last_idx = len(self._screen_positions) - 1
        self.screen_list.selection_clear(0, "end")
        self.screen_list.selection_set(last_idx)
        self.screen_list.activate(last_idx)
        self._on_screen_list_select()
        self.status_var.set(f"Added screen wheel action at ({x}, {y}).")

    def add_screen_wait(self) -> None:
        """Add a wait item to the screen list."""
        wait_ms = self._get_default_wait_ms()
        if wait_ms is None:
            return
        self._screen_positions.append({
            "type": "wait",
            "ms": wait_ms,
        })
        self._refresh_screen_list()
        last_idx = len(self._screen_positions) - 1
        self.screen_list.selection_clear(0, "end")
        self.screen_list.selection_set(last_idx)
        self.screen_list.activate(last_idx)
        self._on_screen_list_select()
        self.status_var.set(f"Added {wait_ms}ms wait.")

    def add_screen_key(self) -> None:
        """Add a key action to the screen list."""
        self._screen_positions.append({
            "type": "key",
            "vk": 0,
            "scan_code": 0,
            "extended": False,
            "key_name": "",
            "modifiers": [],
            "mod_scans": {},
            "delay": None,
        })
        self._refresh_screen_list()
        last_idx = len(self._screen_positions) - 1
        self.screen_list.selection_clear(0, "end")
        self.screen_list.selection_set(last_idx)
        self.screen_list.activate(last_idx)
        self._on_screen_list_select()
        self._begin_key_capture(last_idx, "screen")
        self.status_var.set("Press a key combination...")

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
        ptype = pos.get("type", "click")
        if ptype == "click":
            self.screen_prop_label.config(text="Pos (x,y):")
            self.step_delay_var.set(f"{int(pos['x'])},{int(pos['y'])}")
            self.mouse_button_var.set(pos.get("button", "left"))
            self.custom_delay_var.set(str(pos.get("delay") or ""))
            self.screen_custom_delay_entry.config(state="normal")
            self._set_button_controls_enabled(True)
            self._hide_key_entry()
        elif ptype == "wheel":
            self.screen_prop_label.config(text="Wheel (x,y,delta):")
            self.step_delay_var.set(
                f"{int(pos['x'])},{int(pos['y'])},{coerce_wheel_delta(pos.get('delta'), -1)}"
            )
            self.custom_delay_var.set(str(pos.get("delay") or ""))
            self.screen_custom_delay_entry.config(state="normal")
            self._set_button_controls_enabled(False)
            self._hide_key_entry()
        elif ptype == "key":
            self._show_screen_key_entry()
            self.custom_delay_var.set(str(pos.get("delay") or ""))
            self.screen_custom_delay_entry.config(state="normal")
            self._set_button_controls_enabled(False)
            self._refresh_key_entry_text(sel[0], "screen")
        else:
            self.screen_prop_label.config(text="Wait (ms):")
            self.step_delay_var.set(str(pos.get("ms", 0)))
            self.custom_delay_var.set("")
            self.screen_custom_delay_entry.config(state="disabled")
            self._set_button_controls_enabled(False)
            self._hide_key_entry()

    def remove_screen_position(self) -> None:
        sel = self.screen_list.curselection()
        if not sel:
            return
        index = sel[0]
        if is_position_action(self._screen_positions[index]) and "dot" in self._screen_positions[index]:
            self._screen_positions[index]["dot"].destroy()
        del self._screen_positions[index]
        self._refresh_screen_list()

    def move_screen_position(self, delta: int) -> None:
        sel = self.screen_list.curselection()
        if not sel:
            return
        index = sel[0]
        target = index + delta
        if not 0 <= target < len(self._screen_positions):
            return

        self._screen_positions[index], self._screen_positions[target] = (
            self._screen_positions[target],
            self._screen_positions[index],
        )

        self._refresh_screen_list()
        self.screen_list.selection_set(target)
        self.screen_list.activate(target)
        self._on_screen_list_select()

    def clear_screen_positions(self) -> None:
        for p in self._screen_positions:
            if is_position_action(p) and "dot" in p:
                p["dot"].destroy()
        self._screen_positions.clear()
        self._refresh_screen_list()

    def _refresh_screen_list(self) -> None:
        self.screen_list.delete(0, "end")
        dot_count = 0
        for i, item in enumerate(self._screen_positions):
            if is_position_action(item):
                dot_count += 1
                if "dot" in item:
                    item["dot"].index = i
                    item["dot"].set_number(dot_count)
                self.screen_list.insert(
                    "end",
                    f"{dot_count}: {get_mouse_action_name(item)} - {get_mouse_action_details(item)}",
                )
            else:
                self.screen_list.insert("end", f"   Wait: {item.get('ms', 0)}ms")

    def _refresh_screen_list_item(self, index, append=False):
        if not (0 <= index < len(self._screen_positions)):
            return
        if index >= self.screen_list.size():
            self._refresh_screen_list()
            return
        item = self._screen_positions[index]
        if is_position_action(item):
            dot_count = sum(1 for p in self._screen_positions[: index + 1] if is_position_action(p))
            text = f"{dot_count}: {get_mouse_action_name(item)} - {get_mouse_action_details(item)}"
        else:
            text = f"   Wait: {item.get('ms', 0)}ms"
        had_selection = index in (self.screen_list.curselection() or ())
        self.screen_list.delete(index)
        self.screen_list.insert(index, text)
        if had_selection:
            self.screen_list.selection_set(index)
            self.screen_list.activate(index)

    def add_window_dot(self, at_cursor: bool = False) -> None:
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

        win_w = rect[2] - rect[0]
        win_h = rect[3] - rect[1]

        rel_x, rel_y = None, None
        if at_cursor:
            try:
                pt = POINT()
                if user32.GetCursorPos(ctypes.byref(pt)):
                    rx = pt.x - rect[0]
                    ry = pt.y - rect[1]
                    if 0 <= rx <= win_w and 0 <= ry <= win_h:
                        rel_x, rel_y = rx, ry
            except Exception:
                pass

        if rel_x is None or rel_y is None:
            rel_x, rel_y = win_w // 2, win_h // 2
            bounds = get_client_bounds_in_window(hwnd)
            if bounds:
                rel_x = (bounds[0] + bounds[2]) // 2
                rel_y = (bounds[1] + bounds[3]) // 2

        # Always clamp to client area in minified (client-area-only)
        rel_x, rel_y = clamp_window_position(hwnd, rel_x, rel_y)

        index = len(self._window_positions)
        dot = DraggableDot(self.root, index, rel_x, rel_y, self._on_window_dot_move,
                          on_click=self._on_window_dot_click, hwnd=hwnd, action_type="click")

        self._window_positions.append({
            "type": "click",
            "x": rel_x,
            "y": rel_y,
            "button": "left",
            "delay": None,
            "dot": dot,
            "hwnd": hwnd,
            "win_title": win_data["title"]
        })
        self._refresh_window_pt_list()
        last_idx = len(self._window_positions) - 1
        self.window_pt_list.selection_clear(0, "end")
        self.window_pt_list.selection_set(last_idx)
        self.window_pt_list.activate(last_idx)

        # Keep focus on window list as requested
        self.target_win_list.selection_set(win_idx)
        self.target_win_list.activate(win_idx)

        self.status_var.set(f"Added window dot for '{win_data['title']}' at ({rel_x}, {rel_y}).")

    def add_window_wheel(self, at_cursor: bool = False) -> None:
        """Create a wheel action for the selected window."""
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

        win_w = rect[2] - rect[0]
        win_h = rect[3] - rect[1]

        rel_x, rel_y = None, None
        if at_cursor:
            try:
                pt = POINT()
                if user32.GetCursorPos(ctypes.byref(pt)):
                    rx = pt.x - rect[0]
                    ry = pt.y - rect[1]
                    if 0 <= rx <= win_w and 0 <= ry <= win_h:
                        rel_x, rel_y = rx, ry
            except Exception:
                pass

        if rel_x is None or rel_y is None:
            rel_x, rel_y = win_w // 2, win_h // 2
            bounds = get_client_bounds_in_window(hwnd)
            if bounds:
                rel_x = (bounds[0] + bounds[2]) // 2
                rel_y = (bounds[1] + bounds[3]) // 2

        rel_x, rel_y = clamp_window_position(hwnd, rel_x, rel_y)

        index = len(self._window_positions)
        dot = DraggableDot(self.root, index, rel_x, rel_y, self._on_window_dot_move,
                          on_click=self._on_window_dot_click, hwnd=hwnd, action_type="wheel")

        self._window_positions.append({
            "type": "wheel",
            "x": rel_x,
            "y": rel_y,
            "delta": -1,
            "delay": None,
            "dot": dot,
            "hwnd": hwnd,
            "win_title": win_data["title"]
        })
        self._refresh_window_pt_list()
        last_idx = len(self._window_positions) - 1
        self.window_pt_list.selection_clear(0, "end")
        self.window_pt_list.selection_set(last_idx)
        self.window_pt_list.activate(last_idx)

        self.target_win_list.selection_set(win_idx)
        self.target_win_list.activate(win_idx)

        self.status_var.set(f"Added window wheel action for '{win_data['title']}' at ({rel_x}, {rel_y}).")

    def add_window_wait(self) -> None:
        """Add a wait item to the window list."""
        wait_ms = self._get_default_wait_ms()
        if wait_ms is None:
            return
        self._window_positions.append({
            "type": "wait",
            "ms": wait_ms,
        })
        self._refresh_window_pt_list()
        last_idx = len(self._window_positions) - 1
        self.window_pt_list.selection_clear(0, "end")
        self.window_pt_list.selection_set(last_idx)
        self.window_pt_list.activate(last_idx)
        self._on_window_list_select()
        self.status_var.set(f"Added {wait_ms}ms wait.")

    def add_window_key(self) -> None:
        """Add a key action to the window list."""
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

        self._window_positions.append({
            "type": "key",
            "vk": 0,
            "scan_code": 0,
            "extended": False,
            "key_name": "",
            "modifiers": [],
            "mod_scans": {},
            "delay": None,
            "hwnd": hwnd,
            "win_title": win_data["title"]
        })
        self._refresh_window_pt_list()
        last_idx = len(self._window_positions) - 1
        self.window_pt_list.selection_clear(0, "end")
        self.window_pt_list.selection_set(last_idx)
        self.window_pt_list.activate(last_idx)
        self._on_window_list_select()
        self._begin_key_capture(last_idx, "window")
        self.status_var.set("Press a key combination...")

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
        ptype = pos.get("type", "click")
        if ptype == "click":
            self.window_prop_label.config(text="Pos (x,y):")
            self.step_delay_var.set(f"{int(pos['x'])},{int(pos['y'])}")
            self.mouse_button_var.set(pos.get("button", "left"))
            self.custom_delay_var.set(str(pos.get("delay") or ""))
            self.window_custom_delay_entry.config(state="normal")
            self._set_button_controls_enabled(True)
            self._hide_key_entry()
        elif ptype == "wheel":
            self.window_prop_label.config(text="Wheel (x,y,delta):")
            self.step_delay_var.set(
                f"{int(pos['x'])},{int(pos['y'])},{coerce_wheel_delta(pos.get('delta'), -1)}"
            )
            self.custom_delay_var.set(str(pos.get("delay") or ""))
            self.window_custom_delay_entry.config(state="normal")
            self._set_button_controls_enabled(False)
            self._hide_key_entry()
        elif ptype == "key":
            self._show_window_key_entry()
            self.custom_delay_var.set(str(pos.get("delay") or ""))
            self.window_custom_delay_entry.config(state="normal")
            self._set_button_controls_enabled(False)
            self._refresh_key_entry_text(sel[0], "window")
        else:
            self.window_prop_label.config(text="Wait (ms):")
            self.step_delay_var.set(str(pos.get("ms", 0)))
            self.custom_delay_var.set("")
            self.window_custom_delay_entry.config(state="disabled")
            self._set_button_controls_enabled(False)
            self._hide_key_entry()

    def remove_window_position(self) -> None:
        sel = self.window_pt_list.curselection()
        if not sel:
            return
        index = sel[0]
        if is_position_action(self._window_positions[index]) and "dot" in self._window_positions[index]:
            self._window_positions[index]["dot"].destroy()
        del self._window_positions[index]
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

        self._refresh_window_pt_list()
        self.window_pt_list.selection_set(target)
        self.window_pt_list.activate(target)
        self._on_window_list_select()

    def clear_window_positions(self) -> None:
        for p in self._window_positions:
            if is_position_action(p) and "dot" in p:
                p["dot"].destroy()
        self._window_positions.clear()
        self._refresh_window_pt_list()

    def _refresh_window_pt_list(self) -> None:
        self.window_pt_list.delete(0, "end")
        dot_count = 0
        for i, item in enumerate(self._window_positions):
            if is_position_action(item):
                dot_count += 1
                if "dot" in item:
                    item["dot"].index = i
                    item["dot"].set_number(dot_count)
                title = item.get('win_title', '')
                short = (title[:15] + '..') if len(title) > 15 else title
                self.window_pt_list.insert(
                    "end",
                    f"{dot_count}: {get_mouse_action_name(item)} - {get_mouse_action_details(item, short)}",
                )
            else:
                self.window_pt_list.insert("end", f"   Wait: {item.get('ms', 0)}ms")

    def _refresh_window_pt_item(self, index, append=False):
        if not (0 <= index < len(self._window_positions)):
            return
        if index >= self.window_pt_list.size():
            self._refresh_window_pt_list()
            return
        item = self._window_positions[index]
        if is_position_action(item):
            dot_count = sum(1 for p in self._window_positions[: index + 1] if is_position_action(p))
            title = item.get('win_title', '') or ''
            short = (title[:15] + '..') if len(title) > 15 else title
            text = f"{dot_count}: {get_mouse_action_name(item)} - {get_mouse_action_details(item, short)}"
        else:
            text = f"   Wait: {item.get('ms', 0)}ms"
        had_selection = index in (self.window_pt_list.curselection() or ())
        self.window_pt_list.delete(index)
        self.window_pt_list.insert(index, text)
        if had_selection:
            self.window_pt_list.selection_set(index)
            self.window_pt_list.activate(index)

    def apply_step_delay(self):
        """Save the parameters and custom delay for the selected position in either mode."""
        current_tab = self.notebook.index(self.notebook.select())
        editing_screen = current_tab == 0 or (current_tab == 2 and self._active_mode == "screen")
        if editing_screen:
            sel = self.screen_list.curselection()
            positions = self._screen_positions
        else:
            sel = self.window_pt_list.curselection()
            positions = self._window_positions

        if not sel:
            messagebox.showinfo("Selection Required", "Select a position first.")
            return

        index = sel[0]
        val = self.step_delay_var.get().strip()
        ptype = positions[index].get("type", "click")

        # Parse custom step delay
        custom_delay_str = self.custom_delay_var.get().strip()
        custom_delay = None
        if custom_delay_str:
            try:
                custom_delay = int(custom_delay_str)
                if custom_delay < 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Invalid Step Delay", "Enter a non-negative whole number for custom step delay.")
                return

        try:
            if ptype == "click":
                if val:
                    parts = val.split(',')
                    if len(parts) == 2:
                        positions[index]["x"] = int(parts[0])
                        positions[index]["y"] = int(parts[1])
                positions[index]["button"] = (
                    self.mouse_button_var.get()
                    if self.mouse_button_var.get() in MOUSE_BUTTONS
                    else "left"
                )
                positions[index]["delay"] = custom_delay
            elif ptype == "wheel":
                if val:
                    parts = [p.strip() for p in val.split(',')]
                    if len(parts) == 1:
                        positions[index]["delta"] = coerce_wheel_delta(parts[0], -1)
                    elif len(parts) == 3:
                        positions[index]["x"] = int(parts[0])
                        positions[index]["y"] = int(parts[1])
                        positions[index]["delta"] = coerce_wheel_delta(parts[2], -1)
                    else:
                        raise ValueError
                positions[index]["delay"] = custom_delay
            else:
                if not val:
                    positions[index]["ms"] = 0
                else:
                    ms = int(val)
                    if ms < 0:
                        raise ValueError
                    positions[index]["ms"] = ms
        except ValueError:
            messagebox.showerror("Invalid Value", "Enter ms, x,y for click, or x,y,delta for wheel.")
            return

        # Sync dot screen position if click or wheel
        if ptype in POSITION_ACTION_TYPES and "dot" in positions[index]:
            dot = positions[index]["dot"]
            if dot.hwnd:
                rect = get_window_rect(dot.hwnd)
                if rect:
                    dot.update_position(rect[0] + positions[index]["x"], rect[1] + positions[index]["y"])
            else:
                dot.update_position(positions[index]["x"], positions[index]["y"])

        if editing_screen:
            self._refresh_screen_list()
            self.screen_list.selection_set(index)
        else:
            self._refresh_window_pt_list()
            self.window_pt_list.selection_set(index)
        self.status_var.set(f"Updated item {index+1}.")

    def apply_defaults(self) -> None:
        try:
            interval_ms = int(self.interval_var.get().strip())
            wait_ms = int(self.default_wait_var.get().strip())
            if interval_ms < 0 or wait_ms < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Defaults", "Enter non-negative whole numbers for interval and wait.")
            return

        self.interval_var.set(str(interval_ms))
        self.default_wait_var.set(str(wait_ms))
        self.status_var.set("Defaults updated.")

    def _get_default_wait_ms(self) -> int | None:
        try:
            wait_ms = int(self.default_wait_var.get().strip())
            if wait_ms < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Wait", "Enter a non-negative whole number for the default wait.")
            return None
        self.default_wait_var.set(str(wait_ms))
        return wait_ms

    def reset_hotkeys(self) -> None:
        for action, default in DEFAULT_HOTKEYS.items():
            self.hotkey_vars[action].set(default)
        self._apply_hotkeys()

    def _apply_hotkeys(self, show_status: bool = True) -> bool:
        seen: dict[str, str] = {}
        hotkey_map: dict[str, str] = {}
        for action, label in HOTKEY_ACTIONS:
            hotkey = normalize_hotkey_text(self.hotkey_vars[action].get())
            self.hotkey_vars[action].set(hotkey)
            if not hotkey:
                continue
            if hotkey in seen:
                messagebox.showerror("Duplicate Shortcut", f"{label} and {seen[hotkey]} both use {hotkey}.")
                return False
            seen[hotkey] = label
            hotkey_map[hotkey] = action

        self._hotkey_map = hotkey_map
        if show_status:
            self.status_var.set("Shortcuts updated.")
        return True

    def _on_key_press(self, event) -> str | None:
        hotkey = hotkey_from_event(event)
        action = self._hotkey_map.get(hotkey)
        if not action:
            return None
        if self._handle_hotkey_action(action):
            return "break"
        return None

    def _handle_hotkey_action(self, action: str) -> bool:
        if action == "start":
            self.start_clicking()
        elif action == "stop":
            self.stop_clicking()
        elif action == "add_window":
            self.notebook.select(1)
            self.add_target_window()
        elif action == "add_dot":
            self.add_current_dot()
        elif action == "add_wheel":
            self.add_current_wheel()
        elif action == "add_wait":
            self.add_current_wait()
        elif action == "add_key":
            self.add_current_key()
        elif action == "clear":
            self.clear_current_positions()
        else:
            return False
        return True

    def add_current_dot(self) -> None:
        if self._active_mode == "window":
            self.notebook.select(1)
            self.add_window_dot(at_cursor=True)
        else:
            self.notebook.select(0)
            self.add_screen_dot(at_cursor=True)

    def add_current_wheel(self) -> None:
        if self._active_mode == "window":
            self.notebook.select(1)
            self.add_window_wheel(at_cursor=True)
        else:
            self.notebook.select(0)
            self.add_screen_wheel(at_cursor=True)

    def add_current_wait(self) -> None:
        if self._active_mode == "window":
            self.notebook.select(1)
            self.add_window_wait()
        else:
            self.notebook.select(0)
            self.add_screen_wait()

    def add_current_key(self) -> None:
        if self._active_mode == "window":
            self.notebook.select(1)
            self.add_window_key()
        else:
            self.notebook.select(0)
            self.add_screen_key()

    def clear_current_positions(self) -> None:
        if self._active_mode == "window":
            self.clear_window_positions()
        else:
            self.clear_screen_positions()

    def _install_kb_hook(self) -> None:
        if self._kb_hook:
            return
        try:
            hook_proc = LowLevelKeyboardProc(self._on_low_level_key)
            hmod = kernel32.GetModuleHandleW(None)
            self._kb_hook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, hook_proc, hmod, 0)
            self._kb_hook_proc = hook_proc
        except Exception:
            pass

    def _uninstall_kb_hook(self) -> None:
        if self._kb_hook:
            try:
                user32.UnhookWindowsHookEx(self._kb_hook)
            except Exception:
                pass
            self._kb_hook = None
            self._kb_hook_proc = None

    def _on_low_level_key(self, nCode, wParam, lParam) -> int:
        if nCode == HC_ACTION and self._capturing_key:
            try:
                kb = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
                vk = kb.vkCode
                scan = kb.scanCode
                extended = bool(kb.flags & LLKHF_EXTENDED)
                key_up = bool(kb.flags & LLKHF_UP)

                if key_up:
                    self._safe_after(self._on_key_capture_release, vk)
                else:
                    self._safe_after(self._on_key_capture_press, vk, scan, extended)
                return 1
            except Exception:
                pass
        try:
            return user32.CallNextHookEx(None, nCode, wParam, lParam)
        except Exception:
            return 0

    def _begin_key_capture(self, index: int, mode: str) -> None:
        self._capturing_key = True
        self._key_capture_index = index
        self._key_capture_mode = mode
        self._reset_key_combo_state()
        self._install_kb_hook()
        entry = self._key_entry_for_mode(mode)
        if entry:
            entry.focus_set()

    def _end_key_capture(self) -> None:
        self._capturing_key = False
        self._uninstall_kb_hook()

    def _reset_key_combo_state(self) -> None:
        self._key_pressed_keycodes.clear()
        self._key_combo_modifiers.clear()
        self._key_combo_main = None
        self._key_combo_main_scan = 0
        self._key_combo_main_extended = False
        self._key_combo_mod_scans.clear()

    def _on_key_capture_press(self, vk: int, scan: int, extended: bool) -> None:
        if not self._capturing_key:
            return
        self._key_pressed_keycodes.add(vk)

        mod_name = None
        if vk == 0x10:
            mod_name = "Shift"
        elif vk == 0x11:
            mod_name = "Ctrl"
        elif vk == 0x12:
            mod_name = "Alt"
        elif vk in (VK_LWIN, VK_RWIN):
            mod_name = "Win"

        if mod_name:
            if mod_name not in self._key_combo_modifiers:
                self._key_combo_modifiers.append(mod_name)
                self._key_combo_mod_scans[mod_name] = scan
        else:
            if self._key_combo_main is None:
                key_name_upper = next((k for k, v in VK_MAP.items() if v == vk), None)
                if key_name_upper:
                    if len(key_name_upper) == 1:
                        self._key_combo_main = key_name_upper
                    elif key_name_upper.startswith("F") and key_name_upper[1:].isdigit():
                        self._key_combo_main = key_name_upper
                    else:
                        self._key_combo_main = key_name_upper.capitalize()
                elif 0x30 <= vk <= 0x39:
                    self._key_combo_main = chr(vk)
                elif 0x41 <= vk <= 0x5A:
                    self._key_combo_main = chr(vk)

                if self._key_combo_main:
                    self._key_combo_main_scan = scan
                    self._key_combo_main_extended = extended

        self._refresh_key_entry_text(self._key_capture_index, self._key_capture_mode)

    def _on_key_capture_release(self, vk: int) -> None:
        if not self._capturing_key:
            return
        self._key_pressed_keycodes.discard(vk)

        if not self._key_pressed_keycodes:
            if self._key_combo_main is not None:
                self._commit_key_combo()
            elif self._key_combo_modifiers:
                # Lone modifier(s) released with no main key: promote the
                # last modifier to be the key itself (e.g., just "Ctrl").
                self._promote_lone_modifier()
                self._commit_key_combo()

    def _promote_lone_modifier(self) -> None:
        if not self._key_combo_modifiers:
            return
        primary = self._key_combo_modifiers[-1]
        rest = [m for m in self._key_combo_modifiers if m != primary]
        self._key_combo_main = primary
        self._key_combo_main_scan = self._key_combo_mod_scans.get(primary, 0)
        self._key_combo_main_extended = primary == "Win"
        self._key_combo_modifiers = rest
        self._key_combo_mod_scans.pop(primary, None)

    def _commit_key_combo(self) -> None:
        if not self._capturing_key:
            return

        mode = self._key_capture_mode
        index = self._key_capture_index
        positions = self._screen_positions if mode == "screen" else self._window_positions

        if not (0 <= index < len(positions)):
            self._end_key_capture()
            return

        action = positions[index]
        if action.get("type") != "key":
            self._end_key_capture()
            return

        vk = VK_MAP.get(self._key_combo_main.upper(), 0)
        if vk == 0 and len(self._key_combo_main) == 1:
            vk = ord(self._key_combo_main.upper())

        action["vk"] = vk
        action["scan_code"] = self._key_combo_main_scan
        action["extended"] = self._key_combo_main_extended
        action["key_name"] = self._key_combo_main
        action["modifiers"] = [m for m in ("Ctrl", "Alt", "Shift", "Win") if m in self._key_combo_modifiers]
        action["mod_scans"] = dict(self._key_combo_mod_scans)

        if mode == "screen":
            self._refresh_screen_list_item(index)
        else:
            self._refresh_window_pt_item(index)

        self._refresh_key_entry_text(index, mode)
        self._end_key_capture()
        self.status_var.set(f"Captured: {format_combo(action['modifiers'], action['key_name'])}")

    def _show_screen_key_entry(self) -> None:
        self.screen_prop_label.config(text="Key Combo:")
        self.step_delay_var.set("")
        self._set_button_controls_enabled(False)
        self._hide_key_entry()

    def _show_window_key_entry(self) -> None:
        self.window_prop_label.config(text="Key Combo:")
        self.step_delay_var.set("")
        self._set_button_controls_enabled(False)
        self._hide_key_entry()

    def _hide_key_entry(self) -> None:
        pass

    def _key_entry_for_mode(self, mode: str):
        return self.root

    def _set_key_entry_text(self, text: str) -> None:
        self.step_delay_var.set(text)

    def _refresh_key_entry_text(self, index: int, mode: str) -> None:
        positions = self._screen_positions if mode == "screen" else self._window_positions
        if not (0 <= index < len(positions)):
            return
        action = positions[index]
        if action.get("type") != "key":
            return

        if self._capturing_key and self._key_capture_index == index:
            parts = list(self._key_combo_modifiers)
            if self._key_combo_main:
                parts.append(self._key_combo_main)
            text = "+".join(parts) if parts else "(press a key)"
        else:
            text = format_combo(action.get("modifiers", []), action.get("key_name", "")) or "(empty)"

        self._set_key_entry_text(text)

    def start_clicking(self) -> None:
        if self._click_thread and self._click_thread.is_alive():
            return
            
        current_tab = self.notebook.index(self.notebook.select())
        if current_tab == 0:
            self._active_mode = "screen"
            positions = self._screen_positions
            mode = "screen"
        elif current_tab == 1:
            self._active_mode = "window"
            positions = self._window_positions
            mode = "window"
        else:
            mode = self._active_mode
            positions = self._screen_positions if mode == "screen" else self._window_positions
            
        if mode == "window":
            # Re-resolve target windows with invalid HWNDs by title match before starting
            active_windows = list_visible_windows()
            for w in self._target_windows:
                hwnd = w["hwnd"]
                if not hwnd or not user32.IsWindow(hwnd):
                    found_hwnd = next((h for h, t in active_windows if t == w["title"]), None)
                    if not found_hwnd:
                        found_hwnd = next((h for h, t in active_windows if w["title"].lower() in t.lower()), None)
                    if found_hwnd:
                        w["hwnd"] = found_hwnd
                        for p in self._window_positions:
                            if p.get("win_title") == w["title"]:
                                p["hwnd"] = found_hwnd
                                if "dot" in p:
                                    p["dot"].hwnd = found_hwnd

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

        # Snapshot positions for the thread (preserve all action fields)
        positions_snapshot = []
        for p in positions:
            ptype = p.get("type", "click")
            if ptype == "wait":
                positions_snapshot.append({"type": "wait", "ms": p.get("ms", 0)})
                continue
            snapshot = {
                "type": ptype,
                "x": p["x"],
                "y": p["y"],
                "delay": p.get("delay"),
            }
            if ptype == "click":
                snapshot["button"] = p.get("button", "left")
            elif ptype == "wheel":
                snapshot["delta"] = coerce_wheel_delta(p.get("delta"), -1)
            if mode == "window":
                snapshot["hwnd"] = p.get("hwnd")
                snapshot["win_title"] = p.get("win_title")
            positions_snapshot.append(snapshot)

        # Hide dots while clicking to avoid blocking
        self._set_dots_visible(False)

        loop_enabled = self.loop_var.get()
        self._click_thread = threading.Thread(
            target=self._click_loop, args=(global_interval, positions_snapshot, mode, loop_enabled), daemon=True
        )
        self._click_thread.start()
        
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        
        stop_hotkey = self.hotkey_vars["stop"].get()
        if stop_hotkey:
            self.status_var.set(f"Looping clicks... Press {stop_hotkey} to stop.")
        else:
            self.status_var.set("Looping clicks... (No stop hotkey set)")

    def stop_clicking(self) -> None:
        self._stop_event.set()

    def _set_dots_visible(self, visible: bool):
        # Apply to both modes just in case
        for p in self._screen_positions:
            if not is_position_action(p) or "dot" not in p:
                continue
            if visible: p["dot"].deiconify()
            else: p["dot"].withdraw()
        for p in self._window_positions:
            if not is_position_action(p) or "dot" not in p:
                continue
            if visible: p["dot"].deiconify()
            else: p["dot"].withdraw()

    def _watch_global_hotkeys(self) -> None:
        last_fired: dict[str, float] = {}
        debounce_seconds = 0.4
        while True:
            time.sleep(0.03)
            if not self.enable_global_hotkeys_var.get():
                continue
            try:
                hotkey_map = dict(self._hotkey_map)
            except Exception:
                continue

            now = time.monotonic()
            for hotkey, action in hotkey_map.items():
                if not is_hotkey_pressed_globally(hotkey):
                    continue
                if now - last_fired.get(action, 0.0) < debounce_seconds:
                    continue
                last_fired[action] = now

                if action == "stop":
                    if self._click_thread and self._click_thread.is_alive():
                        self._stop_event.set()
                elif action == "start":
                    if not self._click_thread or not self._click_thread.is_alive():
                        self._safe_after(self.start_clicking)
                else:
                    self._safe_after(self._handle_hotkey_action, action)
                break

    def _safe_after(self, func, *args) -> None:
        try:
            self.root.after(0, func, *args)
        except (RuntimeError, tk.TclError):
            pass

    def _update_hwnd_from_thread(self, title: str, hwnd: int) -> None:
        for w in self._target_windows:
            if w["title"] == title:
                w["hwnd"] = hwnd
        for p in self._window_positions:
            if p.get("win_title") == title:
                p["hwnd"] = hwnd
                if "dot" in p:
                    p["dot"].hwnd = hwnd

    def _click_loop(self, global_interval_ms: int, positions: list[dict], mode: str, loop_enabled: bool) -> None:
        while not self._stop_event.is_set():
            for pos in positions:
                if self._stop_event.is_set():
                    break

                ptype = pos.get("type", "click")

                if ptype == "wait":
                    wait_ms = pos.get("ms", 0)
                    if wait_ms > 0:
                        if self._stop_event.wait(wait_ms / 1000.0):
                            break
                    continue

                if ptype == "key":
                    if mode == "window":
                        hwnd = pos.get("hwnd")
                        if not hwnd or not user32.IsWindow(hwnd):
                            active_windows = list_visible_windows()
                            title = pos.get("win_title")
                            found_hwnd = next((h for h, t in active_windows if t == title), None)
                            if not found_hwnd:
                                found_hwnd = next((h for h, t in active_windows if title and title.lower() in t.lower()), None)
                            if found_hwnd:
                                hwnd = found_hwnd
                                pos["hwnd"] = hwnd
                                if title:
                                    self._safe_after(self._update_hwnd_from_thread, title, hwnd)
                        if hwnd and user32.IsWindow(hwnd):
                            perform_window_key_action(hwnd, pos)
                    else:
                        perform_screen_key_action(pos)

                    delay_ms = pos.get("delay") if pos.get("delay") is not None else global_interval_ms
                    wait_s = delay_ms / 1000.0
                    if wait_s > 0 and self._stop_event.wait(wait_s):
                        break
                    continue

                # Click or wheel -- needs a position and possibly a window
                if mode == "window":
                    hwnd = pos.get("hwnd")
                    if not hwnd or not user32.IsWindow(hwnd):
                        active_windows = list_visible_windows()
                        title = pos.get("win_title")
                        found_hwnd = next((h for h, t in active_windows if t == title), None)
                        if not found_hwnd:
                            found_hwnd = next((h for h, t in active_windows if title and title.lower() in t.lower()), None)
                        if found_hwnd:
                            hwnd = found_hwnd
                            pos["hwnd"] = hwnd
                            if title:
                                self._safe_after(self._update_hwnd_from_thread, title, hwnd)
                    if hwnd and user32.IsWindow(hwnd):
                        rect = get_window_rect(hwnd)
                        if rect:
                            perform_window_mouse_action(hwnd, pos)
                    else:
                        continue
                else:
                    perform_screen_mouse_action(pos)

                # Determine wait time: per-step delay or global interval
                delay_ms = pos.get("delay") if pos.get("delay") is not None else global_interval_ms
                wait_s = delay_ms / 1000.0

                if wait_s > 0 and self._stop_event.wait(wait_s):
                    break

            # If loop is disabled, stop after one full pass
            if not loop_enabled:
                break
            # Yield 1ms each round so configs with all-zero delays don't pin a CPU core
            if self._stop_event.wait(0.001):
                break

        self._safe_after(self._on_loop_exit)

    def _on_loop_exit(self) -> None:
        self._set_dots_visible(True)
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        self.status_var.set("Stopped")

    def _serialize_action(self, action: dict, include_window: bool = False) -> dict:
        action_type = action.get("type", "click")
        if action_type == "click":
            data = {
                "type": "click",
                "x": action.get("x"),
                "y": action.get("y"),
                "button": action.get("button", "left"),
                "delay": action.get("delay"),
            }
        elif action_type == "wheel":
            data = {
                "type": "wheel",
                "x": action.get("x"),
                "y": action.get("y"),
                "delta": coerce_wheel_delta(action.get("delta"), -1),
                "delay": action.get("delay"),
            }
        elif action_type == "key":
            data = {
                "type": "key",
                "vk": action.get("vk", 0),
                "scan_code": action.get("scan_code", 0),
                "extended": action.get("extended", False),
                "key_name": action.get("key_name", ""),
                "modifiers": action.get("modifiers", []),
                "mod_scans": action.get("mod_scans", {}),
                "delay": action.get("delay"),
            }
        else:
            data = {
                "type": "wait",
                "ms": action.get("ms", 0),
            }
        if include_window:
            data["win_title"] = action.get("win_title")
        return data

    def _build_script_data(self) -> dict:
        mode = self._active_mode
        active_positions = self._screen_positions if mode == "screen" else self._window_positions
        return normalize_script_data({
            "mode": mode,
            "global_interval": self.interval_var.get(),
            "loop": self.loop_var.get(),
            "settings": {
                "window_client_area_only": True,
                "enable_global_hotkeys": self.enable_global_hotkeys_var.get(),
                "default_wait_ms": coerce_non_negative_int(self.default_wait_var.get(), DEFAULT_WAIT_MS),
                "hotkeys": {
                    action: normalize_hotkey_text(var.get())
                    for action, var in self.hotkey_vars.items()
                }
            },
            "screen_positions": [self._serialize_action(p) for p in self._screen_positions],
            "target_windows": [w["title"] for w in self._target_windows],
            "window_positions": [self._serialize_action(p, include_window=True) for p in self._window_positions],
            "actions": [self._serialize_action(p, include_window=(mode == "window")) for p in active_positions],
        })

    def export_script(self):
        """Save the current configuration to a JSON file."""
        data = self._build_script_data()

        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Export Script"
        )
        if file_path:
            try:
                write_script_file(file_path, data)
                messagebox.showinfo("Export Successful", f"Script saved to {file_path}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to save script: {e}")

    def _restore_screen_position(self, p_data: dict) -> None:
        ptype = p_data.get("type", "click")
        if ptype == "wait":
            self._screen_positions.append({"type": "wait", "ms": coerce_non_negative_int(p_data.get("ms"), 0)})
            return
        if ptype == "key":
            self._screen_positions.append({
                "type": "key",
                "vk": p_data.get("vk", 0),
                "scan_code": p_data.get("scan_code", 0),
                "extended": p_data.get("extended", False),
                "key_name": p_data.get("key_name", ""),
                "modifiers": p_data.get("modifiers", []),
                "mod_scans": p_data.get("mod_scans", {}),
                "delay": p_data.get("delay"),
            })
            return
        idx = len(self._screen_positions)
        dot = DraggableDot(
            self.root, idx, p_data["x"], p_data["y"],
            self._on_screen_dot_move,
            on_click=self._on_screen_dot_click,
            action_type=ptype,
        )
        entry = {
            "type": ptype,
            "x": p_data["x"],
            "y": p_data["y"],
            "delay": p_data.get("delay"),
            "dot": dot,
        }
        if ptype == "click":
            entry["button"] = p_data.get("button", "left")
        else:
            entry["delta"] = coerce_wheel_delta(p_data.get("delta"), -1)
        self._screen_positions.append(entry)

    def _restore_window_position(self, p_data: dict) -> None:
        ptype = p_data.get("type", "click")
        if ptype == "wait":
            self._window_positions.append({"type": "wait", "ms": coerce_non_negative_int(p_data.get("ms"), 0)})
            return
        win_title = p_data.get("win_title", "")
        if ptype == "key":
            found_hwnd = next((w["hwnd"] for w in self._target_windows if w["title"] == win_title), None)
            self._window_positions.append({
                "type": "key",
                "vk": p_data.get("vk", 0),
                "scan_code": p_data.get("scan_code", 0),
                "extended": p_data.get("extended", False),
                "key_name": p_data.get("key_name", ""),
                "modifiers": p_data.get("modifiers", []),
                "mod_scans": p_data.get("mod_scans", {}),
                "delay": p_data.get("delay"),
                "hwnd": found_hwnd,
                "win_title": win_title,
            })
            return
        found_hwnd = next((w["hwnd"] for w in self._target_windows if w["title"] == win_title), None)
        idx = len(self._window_positions)
        dot = DraggableDot(
            self.root, idx, p_data["x"], p_data["y"],
            self._on_window_dot_move,
            on_click=self._on_window_dot_click,
            hwnd=found_hwnd,
            action_type=ptype,
        )
        entry = {
            "type": ptype,
            "x": p_data["x"],
            "y": p_data["y"],
            "delay": p_data.get("delay"),
            "dot": dot,
            "hwnd": found_hwnd,
            "win_title": win_title,
        }
        if ptype == "click":
            entry["button"] = p_data.get("button", "left")
        else:
            entry["delta"] = coerce_wheel_delta(p_data.get("delta"), -1)
        self._window_positions.append(entry)

    def import_script(self):
        """Load configuration from a JSON file."""
        file_path = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Import Script"
        )
        if not file_path:
            return

        try:
            data = read_script_file(file_path)
        except Exception as e:
            messagebox.showerror("Import Error", f"Failed to read script: {e}")
            return

        # Clear existing
        self.clear_screen_positions()
        self.clear_window_positions()
        self._target_windows.clear()

        # Restore global interval
        self.interval_var.set(data.get("global_interval", "500"))
        self.loop_var.set(data.get("loop", True))

        # Restore hotkeys
        settings = data.get("settings", {})
        self.enable_global_hotkeys_var.set(
            bool(settings.get("enable_global_hotkeys", DEFAULT_ENABLE_GLOBAL_HOTKEYS))
        )
        self.default_wait_var.set(str(settings.get("default_wait_ms", DEFAULT_WAIT_MS)))
        hotkeys = settings.get("hotkeys", {})
        for action, default in DEFAULT_HOTKEYS.items():
            self.hotkey_vars[action].set(hotkeys.get(action, default))
        self._apply_hotkeys(show_status=False)

        # Restore screen positions
        for p_data in data.get("screen_positions", []):
            self._restore_screen_position(p_data)
        self._refresh_screen_list()

        # Restore target windows and re-find HWNDs
        all_active_windows = list_visible_windows()

        missing_windows = []
        for win_title in data.get("target_windows", []):
            found_hwnd = next((h for h, t in all_active_windows if t == win_title), None)
            if found_hwnd:
                self._target_windows.append({"hwnd": found_hwnd, "title": win_title})
            else:
                missing_windows.append(win_title)

        self._refresh_window_list()

        # Restore window positions
        for p_data in data.get("window_positions", []):
            self._restore_window_position(p_data)
        self._refresh_window_pt_list()
        
        if missing_windows:
            messagebox.showwarning(
                "Missing Windows",
                "The following windows could not be found and their points may not work correctly:\n\n" + 
                "\n".join(missing_windows)
            )
        
        self.status_var.set(f"Imported script from {file_path}")

    def save_current_to_auto(self) -> None:
        config_path = get_auto_config_path()
        data = self._build_script_data()
        normalize_script_data(data)
        try:
            timeout_seconds = int(self.auto_loop_timeout_var.get().strip())
            max_rounds = int(self.auto_loop_max_rounds_var.get().strip())
            if timeout_seconds < 0 or max_rounds < 0:
                raise ValueError
        except ValueError:
            timeout_seconds = DEFAULT_AUTO_LOOP_TIMEOUT_SECONDS
            max_rounds = DEFAULT_AUTO_LOOP_MAX_ROUNDS
        data["auto"]["loop_timeout_seconds"] = timeout_seconds
        data["auto"]["loop_max_rounds"] = max_rounds
        data["auto"]["target_wait_seconds"] = DEFAULT_TARGET_WAIT_SECONDS
        try:
            write_script_file(config_path, data)
        except Exception as e:
            messagebox.showerror("Auto Config Error", f"Failed to save auto config: {e}")
            return
        self.status_var.set(f"Auto config saved to {config_path}")

    def open_auto_config_dialog(self) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("Auto Startup Config")
        dialog.resizable(False, False)

        # Center dialog relative to main window
        self.root.update_idletasks()
        dialog.update_idletasks()
        width = 560
        height = 260
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (width // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (height // 2)
        dialog.geometry(f"{width}x{height}+{x}+{y}")

        dialog.transient(self.root)
        dialog.grab_set()

        config_path = get_auto_config_path()
        frame = ttk.Frame(dialog, padding=10)
        frame.pack(fill="both", expand=True)

        path_text = config_path
        if len(path_text) > 72:
            path_text = "..." + path_text[-69:]

        ttk.Label(frame, text="Auto config file").grid(row=0, column=0, sticky="w")
        ttk.Label(frame, text=path_text, foreground="#555555").grid(row=1, column=0, columnspan=3, sticky="w", pady=(2, 10))

        ttk.Label(frame, text="Loop timeout (seconds)").grid(row=2, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.auto_loop_timeout_var, width=10).grid(row=2, column=1, sticky="w", padx=(8, 0))

        ttk.Label(frame, text="Max loop rounds").grid(row=3, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(frame, textvariable=self.auto_loop_max_rounds_var, width=10).grid(row=3, column=1, sticky="w", padx=(8, 0), pady=(8, 0))

        status_var = tk.StringVar()
        if os.path.exists(config_path):
            try:
                existing = read_script_file(config_path)
                auto = existing.get("auto", {})
                self.auto_loop_timeout_var.set(str(auto.get("loop_timeout_seconds", DEFAULT_AUTO_LOOP_TIMEOUT_SECONDS)))
                self.auto_loop_max_rounds_var.set(str(auto.get("loop_max_rounds", DEFAULT_AUTO_LOOP_MAX_ROUNDS)))
                status_var.set("Existing auto config loaded.")
            except Exception as e:
                status_var.set(f"Existing auto config is invalid: {e}")
        else:
            status_var.set("No auto config saved yet.")

        def apply_auto_limits(data: dict) -> dict | None:
            try:
                timeout_seconds = int(self.auto_loop_timeout_var.get().strip())
                max_rounds = int(self.auto_loop_max_rounds_var.get().strip())
                if timeout_seconds < 0 or max_rounds < 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Invalid Auto Limits", "Enter non-negative whole numbers for timeout and rounds.")
                return None

            normalize_script_data(data)
            data["auto"]["loop_timeout_seconds"] = timeout_seconds
            data["auto"]["loop_max_rounds"] = max_rounds
            data["auto"]["target_wait_seconds"] = DEFAULT_TARGET_WAIT_SECONDS
            return data

        def save_data_to_auto(data: dict, success_message: str) -> None:
            data = apply_auto_limits(data)
            if data is None:
                return
            try:
                write_script_file(config_path, data)
            except Exception as e:
                messagebox.showerror("Auto Config Error", f"Failed to save auto config: {e}")
                return
            status_var.set(success_message)
            self.status_var.set(success_message)

        def import_to_auto() -> None:
            file_path = filedialog.askopenfilename(
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                title="Import Script To Auto Config",
            )
            if not file_path:
                return
            try:
                data = read_script_file(file_path)
            except Exception as e:
                messagebox.showerror("Import Error", f"Failed to read script: {e}")
                return
            save_data_to_auto(data, f"Auto config imported from {file_path}")

        def save_current_to_auto_inner() -> None:
            save_data_to_auto(self._build_script_data(), "Current setup saved as auto config.")

        def clear_auto_config() -> None:
            if os.path.exists(config_path):
                try:
                    os.remove(config_path)
                except Exception as e:
                    messagebox.showerror("Auto Config Error", f"Failed to remove auto config: {e}")
                    return
            status_var.set("Auto config cleared.")
            self.status_var.set("Auto config cleared.")

        button_row = ttk.Frame(frame)
        button_row.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(14, 0))
        ttk.Button(button_row, text="Import Script", command=import_to_auto).pack(side="left")
        ttk.Button(button_row, text="Save Current", command=save_current_to_auto_inner).pack(side="left", padx=(6, 0))
        ttk.Button(button_row, text="Clear", command=clear_auto_config).pack(side="left", padx=(6, 0))
        ttk.Button(button_row, text="Close", command=dialog.destroy).pack(side="right", padx=(20, 0))

        ttk.Label(frame, textvariable=status_var, foreground="#005a9e").grid(
            row=5,
            column=0,
            columnspan=3,
            sticky="w",
            pady=(12, 0),
        )

    def on_close(self) -> None:
        self._stop_event.set()
        self._uninstall_kb_hook()
        thread = self._click_thread
        if thread and thread.is_alive():
            thread.join(timeout=1.0)
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()
