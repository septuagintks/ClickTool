import ctypes
from ctypes import wintypes
import argparse
from datetime import datetime
import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import time

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# WinAPI Constants
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_RBUTTONDOWN = 0x0204
WM_RBUTTONUP = 0x0205
WM_MBUTTONDOWN = 0x0207
WM_MBUTTONUP = 0x0208
WM_MOUSEWHEEL = 0x020A
WM_XBUTTONDOWN = 0x020B
WM_XBUTTONUP = 0x020C
VK_ESCAPE = 0x1B
MK_LBUTTON = 0x0001

INPUT_MOUSE = 0
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_XDOWN = 0x0080
MOUSEEVENTF_XUP = 0x0100
MOUSEEVENTF_WHEEL = 0x0800
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
user32.GetCursorPos.argtypes = [ctypes.POINTER(POINT)]
user32.GetCursorPos.restype = wintypes.BOOL
user32.WindowFromPoint.argtypes = [POINT]
user32.WindowFromPoint.restype = wintypes.HWND
user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
user32.GetAncestor.restype = wintypes.HWND
user32.GetParent.argtypes = [wintypes.HWND]
user32.GetParent.restype = wintypes.HWND

CWP_ALL = 0x0000
CWP_SKIPINVISIBLE = 0x0001

def makelong(low, high):
    return (low & 0xFFFF) | ((high & 0xFFFF) << 16)

def perform_screen_mouse_action(action: dict) -> bool:
    """Perform a screen-space click or wheel action via SendInput."""
    action_type = action.get("type", "click")
    x = int(action["x"])
    y = int(action["y"])

    screen_w = user32.GetSystemMetrics(SM_CXSCREEN)
    screen_h = user32.GetSystemMetrics(SM_CYSCREEN)
    nx = int(x * 65535 / max(1, screen_w - 1))
    ny = int(y * 65535 / max(1, screen_h - 1))

    inp_move = INPUT()
    inp_move.type = INPUT_MOUSE
    inp_move.iu.mi = MOUSEINPUT(nx, ny, 0, MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, 0, None)

    if action_type == "click":
        button = action.get("button", "left")
        down_flag, up_flag, mouse_data = BUTTON_INPUT_MAP.get(button, BUTTON_INPUT_MAP["left"])

        inp_down = INPUT()
        inp_down.type = INPUT_MOUSE
        inp_down.iu.mi = MOUSEINPUT(0, 0, mouse_data, down_flag, 0, None)

        inp_up = INPUT()
        inp_up.type = INPUT_MOUSE
        inp_up.iu.mi = MOUSEINPUT(0, 0, mouse_data, up_flag, 0, None)

        inputs = (INPUT * 3)(inp_move, inp_down, inp_up)
        user32.SendInput(3, inputs, ctypes.sizeof(INPUT))
        return True

    if action_type == "wheel":
        delta = coerce_wheel_delta(action.get("delta"), -1)
        inp_wheel = INPUT()
        inp_wheel.type = INPUT_MOUSE
        inp_wheel.iu.mi = MOUSEINPUT(0, 0, delta * WHEEL_DELTA, MOUSEEVENTF_WHEEL, 0, None)
        inputs = (INPUT * 2)(inp_move, inp_wheel)
        user32.SendInput(2, inputs, ctypes.sizeof(INPUT))
        return True

    return False

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


user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = ctypes.c_short
kernel32.GetCurrentThreadId.restype = wintypes.DWORD
kernel32.GetModuleHandleW.restype = wintypes.HMODULE
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.CreateMutexW.restype = wintypes.HANDLE
kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.GetLastError.restype = wintypes.DWORD
kernel32.ReleaseMutex.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]

VK_MAP = {
    "ESC": 0x1B,
    "ENTER": 0x0D,
    "SPACE": 0x20,
    "TAB": 0x09,
    "DELETE": 0x2E,
    "BACKSPACE": 0x08,
    "PAGEUP": 0x21,
    "PAGEDOWN": 0x22,
    "END": 0x23,
    "HOME": 0x24,
    "LEFT": 0x25,
    "UP": 0x26,
    "RIGHT": 0x27,
    "DOWN": 0x28,
    "INSERT": 0x2D,
    ",": 0xBC,
    ".": 0xBE,
    "/": 0xBF,
    ";": 0xBA,
    "'": 0xDE,
    "[": 0xDB,
    "]": 0xDD,
    "\\": 0xDC,
    "-": 0xBD,
    "=": 0xBB,
    "`": 0xC0,
}
for i in range(1, 13):
    VK_MAP[f"F{i}"] = 0x70 + (i - 1)
for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
    VK_MAP[c] = ord(c)
for c in "0123456789":
    VK_MAP[c] = ord(c)

DEFAULT_HOTKEYS = {
    "start": "F8",
    "stop": "Esc",
    "add_window": "Ctrl+Shift+W",
    "add_dot": "Ctrl+D",
    "add_wheel": "Ctrl+Shift+D",
    "add_wait": "Ctrl+W",
    "clear": "Ctrl+Delete",
}

HOTKEY_ACTIONS = (
    ("start", "Start"),
    ("stop", "Stop"),
    ("add_window", "Add Window"),
    ("add_dot", "Add Dot"),
    ("add_wheel", "Add Wheel"),
    ("add_wait", "Add Wait"),
    ("clear", "Clear"),
)

MODIFIER_STATE_BITS = {
    "Shift": 0x0001,
    "Ctrl": 0x0004,
    "Alt": 0x0008,
}
MODIFIER_KEYS = {"Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R", "Meta_L", "Meta_R"}


def is_hotkey_pressed_globally(hotkey_str: str) -> bool:
    if not hotkey_str:
        return False
    parts = [p.strip().upper() for p in hotkey_str.split("+") if p.strip()]
    if not parts:
        return False
    modifiers_needed = {
        "CTRL": 0x11,  # VK_CONTROL
        "ALT": 0x12,   # VK_MENU
        "SHIFT": 0x10, # VK_SHIFT
    }
    for mod_name, vk_code in modifiers_needed.items():
        is_pressed = (user32.GetAsyncKeyState(vk_code) & 0x8000) != 0
        if mod_name in parts:
            if not is_pressed:
                return False
        else:
            if is_pressed:
                return False
    main_keys = [p for p in parts if p not in modifiers_needed]
    if not main_keys:
        return False
    main_key_str = main_keys[0]
    vk = VK_MAP.get(main_key_str)
    if vk is None:
        if len(main_key_str) == 1:
            vk = ord(main_key_str)
        else:
            return False
    return (user32.GetAsyncKeyState(vk) & 0x8000) != 0


def canonical_key_name(key: str) -> str:
    if len(key) == 1:
        return key.upper()
    if key.lower().startswith("f") and key[1:].isdigit():
        return key.upper()
    return key[:1].upper() + key[1:]


def normalize_hotkey_text(value) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    text = text.strip("<>")
    text = text.replace("-", "+")
    parts = [part.strip() for part in text.split("+") if part.strip()]
    if not parts:
        return ""

    aliases = {
        "control": "Ctrl",
        "ctrl": "Ctrl",
        "shift": "Shift",
        "alt": "Alt",
        "option": "Alt",
        "escape": "Esc",
        "esc": "Esc",
        "return": "Enter",
        "enter": "Enter",
        "delete": "Delete",
        "del": "Delete",
        "space": "Space",
        "tab": "Tab",
    }

    modifiers: list[str] = []
    key = ""
    for part in parts:
        mapped = aliases.get(part.lower())
        if mapped in MODIFIER_STATE_BITS:
            if mapped not in modifiers:
                modifiers.append(mapped)
        else:
            key = mapped or canonical_key_name(part)

    if not key:
        return ""
    ordered_modifiers = [name for name in ("Ctrl", "Alt", "Shift") if name in modifiers]
    return "+".join([*ordered_modifiers, key])


def hotkey_from_event(event) -> str:
    if event.keysym in MODIFIER_KEYS:
        return ""
    key = {
        "Escape": "Esc",
        "Return": "Enter",
        "space": "Space",
    }.get(event.keysym, canonical_key_name(event.keysym))
    modifiers = [
        name
        for name in ("Ctrl", "Alt", "Shift")
        if event.state & MODIFIER_STATE_BITS[name]
    ]
    return "+".join([*modifiers, key])

DOT_SIZE = 40
APP_NAME = "ClickTool"
AUTO_CONFIG_FILENAME = "auto_config.json"
AUTO_LOG_DIRNAME = "logs"
DEFAULT_AUTO_LOOP_TIMEOUT_SECONDS = 60
DEFAULT_AUTO_LOOP_MAX_ROUNDS = 3
DEFAULT_TARGET_WAIT_SECONDS = 60
DEFAULT_INTERVAL_MS = 500
DEFAULT_WAIT_MS = 500
ERROR_ALREADY_EXISTS = 183
WHEEL_DELTA = 120
XBUTTON1 = 0x0001
XBUTTON2 = 0x0002
MK_XBUTTON1 = 0x0020
MK_XBUTTON2 = 0x0040
POSITION_ACTION_TYPES = {"click", "wheel"}
MOUSE_BUTTONS = ("left", "right", "middle", "x1", "x2")
MOUSE_BUTTON_LABELS = {
    "left": "Left",
    "right": "Right",
    "middle": "Middle",
    "x1": "Side 1",
    "x2": "Side 2",
}
BUTTON_MESSAGE_MAP = {
    "left": (WM_LBUTTONDOWN, WM_LBUTTONUP, MK_LBUTTON, 0, 0),
    "right": (WM_RBUTTONDOWN, WM_RBUTTONUP, 0x0002, 0, 0),  # MK_RBUTTON
    "middle": (WM_MBUTTONDOWN, WM_MBUTTONUP, 0x0010, 0, 0),  # MK_MBUTTON
    "x1": (WM_XBUTTONDOWN, WM_XBUTTONUP, MK_XBUTTON1, XBUTTON1, XBUTTON1),
    "x2": (WM_XBUTTONDOWN, WM_XBUTTONUP, MK_XBUTTON2, XBUTTON2, XBUTTON2),
}
BUTTON_INPUT_MAP = {
    "left": (MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP, 0),
    "right": (MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP, 0),
    "middle": (MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP, 0),
    "x1": (MOUSEEVENTF_XDOWN, MOUSEEVENTF_XUP, XBUTTON1),
    "x2": (MOUSEEVENTF_XDOWN, MOUSEEVENTF_XUP, XBUTTON2),
}

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


def get_client_bounds_in_window(hwnd):
    rect = get_window_rect(hwnd)
    client_rect = get_client_rect(hwnd)
    if not rect or not client_rect:
        return None
    client_left, client_top = client_to_screen(hwnd, client_rect[0], client_rect[1])
    left = client_left - rect[0]
    top = client_top - rect[1]
    return (left, top, left + client_rect[2] - client_rect[0], top + client_rect[3] - client_rect[1])


def clamp_window_position(hwnd: int, x: int, y: int) -> tuple[int, int]:
    bounds = get_client_bounds_in_window(hwnd)
    if bounds is None:
        rect = get_window_rect(hwnd)
        if not rect:
            return int(x), int(y)
        bounds = (0, 0, rect[2] - rect[0], rect[3] - rect[1])
    return (max(bounds[0], min(int(x), bounds[2])), max(bounds[1], min(int(y), bounds[3])))


def get_app_data_dir() -> str:
    base_dir = os.environ.get("LOCALAPPDATA")
    if not base_dir:
        base_dir = os.path.join(os.path.expanduser("~"), "AppData", "Local")
    return os.path.join(base_dir, APP_NAME)


def get_auto_config_path() -> str:
    return os.path.join(get_app_data_dir(), AUTO_CONFIG_FILENAME)


def get_auto_log_path() -> str:
    log_dir = os.path.join(get_app_data_dir(), AUTO_LOG_DIRNAME)
    os.makedirs(log_dir, exist_ok=True)
    return os.path.join(log_dir, "auto-minified.log")


def write_auto_log(log_path: str | None, message: str) -> None:
    if not log_path:
        return
    try:
        if os.path.exists(log_path) and os.path.getsize(log_path) > 1024 * 1024:
            old_path = log_path + ".old"
            if os.path.exists(old_path):
                os.remove(old_path)
            os.rename(log_path, old_path)
    except Exception:
        pass
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {message}\n")
    except Exception:
        pass


def coerce_non_negative_int(value, default: int) -> int:
    try:
        value = int(value)
    except (TypeError, ValueError):
        return default
    return max(0, value)


def is_position_action(action: dict) -> bool:
    return action.get("type", "click") in POSITION_ACTION_TYPES


def normalize_mouse_action(action: dict) -> dict:
    action_type = action.get("type", "click")
    if action_type == "click":
        button = str(action.get("button", "left")).lower()
        action["button"] = button if button in MOUSE_BUTTONS else "left"
    elif action_type == "wheel":
        action["delta"] = coerce_wheel_delta(action.get("delta"), -1)
    return action


def coerce_wheel_delta(value, default: int) -> int:
    try:
        value = int(value)
    except (TypeError, ValueError):
        return default
    return value if value != 0 else default


def get_mouse_action_name(action: dict) -> str:
    action_type = action.get("type", "click")
    if action_type == "click":
        button = action.get("button", "left")
        return f"Click {MOUSE_BUTTON_LABELS.get(button, 'Left')}"
    if action_type == "wheel":
        delta = coerce_wheel_delta(action.get("delta"), -1)
        direction = "Up" if delta > 0 else "Down"
        return f"Wheel {direction}"
    return "Wait"


def get_mouse_action_details(action: dict, title: str | None = None) -> str:
    prefix = f"[{title}] " if title else ""
    action_type = action.get("type", "click")
    suffix = ""
    if action.get("delay") is not None:
        suffix = f" (+{action['delay']}ms)"
    if action_type == "click":
        button = MOUSE_BUTTON_LABELS.get(action.get("button", "left"), "Left")
        return f"{prefix}{button} at ({int(action['x'])}, {int(action['y'])}){suffix}"
    if action_type == "wheel":
        delta = coerce_wheel_delta(action.get("delta"), -1)
        return f"{prefix}Delta {delta} at ({int(action['x'])}, {int(action['y'])}){suffix}"
    return f"Delay: {action['ms']}ms"


def normalize_script_data(data: dict) -> dict:
    if "mode" not in data:
        data["mode"] = "window" if data.get("window_positions") else "screen"
    settings = data.setdefault("settings", {})
    settings["window_client_area_only"] = True
    settings["default_wait_ms"] = coerce_non_negative_int(
        settings.get("default_wait_ms"), DEFAULT_WAIT_MS
    )
    auto = data.setdefault("auto", {})
    auto["loop_timeout_seconds"] = coerce_non_negative_int(
        auto.get("loop_timeout_seconds"), DEFAULT_AUTO_LOOP_TIMEOUT_SECONDS
    )
    auto["loop_max_rounds"] = coerce_non_negative_int(
        auto.get("loop_max_rounds"), DEFAULT_AUTO_LOOP_MAX_ROUNDS
    )
    auto["target_wait_seconds"] = coerce_non_negative_int(
        auto.get("target_wait_seconds"), DEFAULT_TARGET_WAIT_SECONDS
    )
    hotkeys = settings.setdefault("hotkeys", {})
    for action, default in DEFAULT_HOTKEYS.items():
        hotkeys[action] = normalize_hotkey_text(hotkeys.get(action, default))

    for collection_name in ("screen_positions", "window_positions", "actions"):
        for action in data.get(collection_name, []):
            normalize_mouse_action(action)
    return data


def read_script_file(file_path: str) -> dict:
    with open(file_path, "r", encoding="utf-8-sig") as f:
        data = json.load(f)
    normalize_script_data(data)
    return data


def write_script_file(file_path: str, data: dict) -> None:
    directory = os.path.dirname(file_path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    temp_path = file_path + ".tmp"
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        os.replace(temp_path, file_path)
    except Exception as e:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
        raise e


def acquire_single_instance_mutex() -> int | None:
    mutex_name = f"Local\\{APP_NAME}SingleInstance"
    handle = kernel32.CreateMutexW(None, True, mutex_name)
    if not handle:
        return None
    if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        kernel32.CloseHandle(handle)
        return None
    return handle


def release_single_instance_mutex(handle: int | None) -> None:
    if handle:
        kernel32.ReleaseMutex(handle)
        kernel32.CloseHandle(handle)


def sleep_until_deadline(seconds: float, deadline: float | None) -> None:
    if seconds <= 0:
        return
    if deadline is None:
        time.sleep(seconds)
        return

    remaining = deadline - time.monotonic()
    if remaining > 0:
        time.sleep(min(seconds, remaining))


def show_already_running_message() -> None:
    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo("Already Running", "Click Tool is already running.")
    root.destroy()


def list_visible_windows() -> list[tuple[int, str]]:
    windows: list[tuple[int, str]] = []

    def enum_callback(hwnd, lparam):
        if user32.IsWindowVisible(hwnd):
            title = get_window_title(hwnd)
            if title:
                windows.append((hwnd, title))
        return True

    user32.EnumWindows(EnumWindowsProc(enum_callback), 0)
    return windows


def find_windows_by_titles(titles: list[str]) -> dict[str, int]:
    active_windows = list_visible_windows()
    found: dict[str, int] = {}
    for title in titles:
        hwnd = next((h for h, t in active_windows if t == title), None)
        if hwnd is None:
            title_lower = title.lower()
            hwnd = next((h for h, t in active_windows if title_lower in t.lower()), None)
        if hwnd:
            found[title] = hwnd
    return found


def wait_for_windows(titles: list[str], timeout_seconds: int, log_path: str | None = None) -> dict[str, int]:
    if not titles:
        return {}
    deadline = time.monotonic() + timeout_seconds
    while True:
        found = find_windows_by_titles(titles)
        missing = [title for title in titles if title not in found]
        write_auto_log(log_path, f"waiting for windows; found={list(found.keys())}; missing={missing}")
        if not missing:
            return found
        if timeout_seconds <= 0 or time.monotonic() >= deadline:
            return found
        time.sleep(1)


def make_wparam(low_word: int, high_word: int) -> int:
    return ((int(high_word) & 0xFFFF) << 16) | (int(low_word) & 0xFFFF)


def post_window_mouse_action(target_hwnd: int, action: dict, client_x: int, client_y: int, screen_x: int, screen_y: int) -> bool:
    action_type = action.get("type", "click")
    if action_type == "click":
        button = action.get("button", "left")
        down_msg, up_msg, down_low_word, down_high_word, up_high_word = BUTTON_MESSAGE_MAP.get(
            button,
            BUTTON_MESSAGE_MAP["left"],
        )
        lparam = makelong(client_x, client_y)
        user32.PostMessageW(target_hwnd, down_msg, make_wparam(down_low_word, down_high_word), lparam)
        user32.PostMessageW(target_hwnd, up_msg, make_wparam(0, up_high_word), lparam)
        return True

    if action_type == "wheel":
        delta = coerce_wheel_delta(action.get("delta"), -1)
        user32.PostMessageW(
            target_hwnd,
            WM_MOUSEWHEEL,
            make_wparam(0, delta * WHEEL_DELTA),
            makelong(screen_x, screen_y),
        )
        return True

    return False


def perform_window_mouse_action(hwnd: int, action: dict) -> bool:
    """Perform a window-relative click or wheel action via PostMessage. Client-area only."""
    if not hwnd or not user32.IsWindow(hwnd):
        return False
    rect = get_window_rect(hwnd)
    bounds = get_client_bounds_in_window(hwnd)
    if not rect or not bounds:
        return False
    x = int(action["x"])
    y = int(action["y"])
    if not (bounds[0] <= x <= bounds[2] and bounds[1] <= y <= bounds[3]):
        return False

    normalize_mouse_action(action)
    sx = int(rect[0] + x)
    sy = int(rect[1] + y)
    cl_tl = POINT(0, 0)
    user32.ClientToScreen(hwnd, ctypes.byref(cl_tl))
    cx = int(sx - cl_tl.x)
    cy = int(sy - cl_tl.y)
    target_hwnd = user32.ChildWindowFromPointEx(hwnd, POINT(cx, cy), CWP_SKIPINVISIBLE) or hwnd

    t_cl_tl = POINT(0, 0)
    user32.ClientToScreen(target_hwnd, ctypes.byref(t_cl_tl))
    tx = int(sx - t_cl_tl.x)
    ty = int(sy - t_cl_tl.y)
    return post_window_mouse_action(target_hwnd, action, tx, ty, sx, sy)


def click_window_position(hwnd: int, x: int, y: int, button: str = "left") -> bool:
    """Backward-compatible left click helper."""
    return perform_window_mouse_action(hwnd, {"type": "click", "x": x, "y": y, "button": button})

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
        self.root.minsize(680, 520)

        self.interval_var = tk.StringVar(value=str(DEFAULT_INTERVAL_MS))
        self.default_wait_var = tk.StringVar(value=str(DEFAULT_WAIT_MS))
        self.step_delay_var = tk.StringVar()
        self.custom_delay_var = tk.StringVar()
        self.mouse_button_var = tk.StringVar(value="left")
        self.loop_var = tk.BooleanVar(value=True)
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
        # Notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True)
        
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

        # Global Run controls and Status
        bottom_frame = ttk.Frame(self.root, padding=(8, 0, 8, 8))
        bottom_frame.pack(fill="x")
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

    def _build_settings_ui(self, frame) -> None:
        frame.columnconfigure(0, weight=1)
        info = ttk.LabelFrame(frame, text="Window Mode", padding=10)
        info.grid(row=0, column=0, sticky="ew")
        ttk.Label(info, text="Window Mode is client-area only in the minified build.").grid(row=0, column=0, sticky="w")
        ttk.Label(
            info,
            text="Title bars, minimize, maximize, and close buttons are intentionally unsupported to keep clicks pure background and dependency-free.",
            foreground="#555555",
            wraplength=500,
        ).grid(row=1, column=0, sticky="ew", pady=(4, 0))

        defaults_frame = ttk.LabelFrame(frame, text="Defaults", padding=10)
        defaults_frame.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        defaults_frame.columnconfigure(1, weight=1)
        ttk.Label(defaults_frame, text="Interval (ms)").grid(row=0, column=0, sticky="w")
        ttk.Entry(defaults_frame, textvariable=self.interval_var, width=10).grid(row=0, column=1, sticky="w", padx=(8, 18))
        ttk.Label(defaults_frame, text="Wait item (ms)").grid(row=0, column=2, sticky="w")
        ttk.Entry(defaults_frame, textvariable=self.default_wait_var, width=10).grid(row=0, column=3, sticky="w", padx=(8, 0))
        ttk.Button(defaults_frame, text="Apply", command=self.apply_defaults).grid(row=0, column=4, sticky="e", padx=(16, 0))

        hotkey_frame = ttk.LabelFrame(frame, text="Shortcuts", padding=10)
        hotkey_frame.grid(row=2, column=0, sticky="ew", pady=(8, 0))
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
        
        # Left: Window Column
        win_frame = ttk.Frame(paned, padding=(0, 0, 8, 0))
        paned.add(win_frame, weight=1)
        
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
        else:
            self._set_dots_visible(False)
            
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
                            p["x"], p["y"] = clamp_window_position(hwnd, p["x"], p["y"])
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
            screen_w = user32.GetSystemMetrics(0)
            screen_h = user32.GetSystemMetrics(1)
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
            screen_w = user32.GetSystemMetrics(0)
            screen_h = user32.GetSystemMetrics(1)
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
        elif ptype == "wheel":
            self.screen_prop_label.config(text="Wheel (x,y,delta):")
            self.step_delay_var.set(
                f"{int(pos['x'])},{int(pos['y'])},{coerce_wheel_delta(pos.get('delta'), -1)}"
            )
            self.custom_delay_var.set(str(pos.get("delay") or ""))
            self.screen_custom_delay_entry.config(state="normal")
            self._set_button_controls_enabled(False)
        else:
            self.screen_prop_label.config(text="Wait (ms):")
            self.step_delay_var.set(str(pos.get("ms", 0)))
            self.custom_delay_var.set("")
            self.screen_custom_delay_entry.config(state="disabled")
            self._set_button_controls_enabled(False)

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
        # The append fast-path is no longer used — wheel/wait reorder dot numbering.
        self._refresh_screen_list()

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
        elif ptype == "wheel":
            self.window_prop_label.config(text="Wheel (x,y,delta):")
            self.step_delay_var.set(
                f"{int(pos['x'])},{int(pos['y'])},{coerce_wheel_delta(pos.get('delta'), -1)}"
            )
            self.custom_delay_var.set(str(pos.get("delay") or ""))
            self.window_custom_delay_entry.config(state="normal")
            self._set_button_controls_enabled(False)
        else:
            self.window_prop_label.config(text="Wait (ms):")
            self.step_delay_var.set(str(pos.get("ms", 0)))
            self.custom_delay_var.set("")
            self.window_custom_delay_entry.config(state="disabled")
            self._set_button_controls_enabled(False)

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
        self._refresh_window_pt_list()

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

    def clear_current_positions(self) -> None:
        if self._active_mode == "window":
            self.clear_window_positions()
        else:
            self.clear_screen_positions()

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
                        self.root.after(0, self.start_clicking)
                else:
                    self.root.after(0, self._handle_hotkey_action, action)
                break

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

                # Click or wheel — needs a position and possibly a window
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
                                self.root.after(0, self._update_hwnd_from_thread, title, hwnd)
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

        self.root.after(0, self._on_loop_exit)

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
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def run_auto_config(config_path: str, log_path: str | None = None) -> int:
    write_auto_log(log_path, f"auto run started; config={config_path}")
    if not os.path.exists(config_path):
        write_auto_log(log_path, "auto config not found; exit=2")
        return 2
    try:
        data = read_script_file(config_path)
    except Exception as e:
        write_auto_log(log_path, f"failed to read config: {e}; exit=2")
        return 2

    mode = data.get("mode", "window" if data.get("window_positions") else "screen")
    loop_enabled = bool(data.get("loop", True))
    global_interval_ms = coerce_non_negative_int(data.get("global_interval"), 500)
    auto = data.get("auto", {})
    timeout_seconds = coerce_non_negative_int(auto.get("loop_timeout_seconds"), DEFAULT_AUTO_LOOP_TIMEOUT_SECONDS)
    max_rounds = coerce_non_negative_int(auto.get("loop_max_rounds"), DEFAULT_AUTO_LOOP_MAX_ROUNDS)
    target_wait_seconds = coerce_non_negative_int(auto.get("target_wait_seconds"), DEFAULT_TARGET_WAIT_SECONDS)
    if loop_enabled and timeout_seconds == 0 and max_rounds == 0:
        timeout_seconds = DEFAULT_AUTO_LOOP_TIMEOUT_SECONDS
        max_rounds = DEFAULT_AUTO_LOOP_MAX_ROUNDS

    write_auto_log(log_path, f"loaded config; mode={mode}; loop={loop_enabled}; timeout={timeout_seconds}; rounds={max_rounds}; wait={target_wait_seconds}")

    fallback_actions = data.get("window_positions", []) if mode == "window" else data.get("screen_positions", [])
    raw_actions = data.get("actions") or fallback_actions

    if mode == "window":
        titles = set(data.get("target_windows", []))
        titles.update(p.get("win_title") for p in fallback_actions if p.get("win_title"))
        titles = sorted(titles)
        window_map = wait_for_windows(titles, target_wait_seconds, log_path)
        actions = []
        for p in raw_actions:
            normalize_mouse_action(p)
            ptype = p.get("type", "click")
            if ptype == "wait":
                actions.append({"type": "wait", "ms": coerce_non_negative_int(p.get("ms"), 0)})
                continue
            hwnd = window_map.get(p.get("win_title"))
            if hwnd:
                entry = {
                    "type": ptype,
                    "hwnd": hwnd,
                    "x": p["x"],
                    "y": p["y"],
                    "delay": p.get("delay"),
                    "win_title": p.get("win_title"),
                }
                if ptype == "click":
                    entry["button"] = p.get("button", "left")
                else:
                    entry["delta"] = coerce_wheel_delta(p.get("delta"), -1)
                actions.append(entry)
            else:
                write_auto_log(log_path, f"missing window position title={p.get('win_title')}")
    else:
        actions = []
        for p in raw_actions:
            normalize_mouse_action(p)
            ptype = p.get("type", "click")
            if ptype == "wait":
                actions.append({"type": "wait", "ms": coerce_non_negative_int(p.get("ms"), 0)})
                continue
            entry = {
                "type": ptype,
                "x": p["x"],
                "y": p["y"],
                "delay": p.get("delay"),
            }
            if ptype == "click":
                entry["button"] = p.get("button", "left")
            else:
                entry["delta"] = coerce_wheel_delta(p.get("delta"), -1)
            actions.append(entry)

    runnable_count = sum(1 for a in actions if is_position_action(a))
    if not runnable_count:
        write_auto_log(log_path, "no runnable actions; exit=3")
        return 3

    deadline = time.monotonic() + timeout_seconds if loop_enabled and timeout_seconds > 0 else None
    rounds = 0
    while True:
        clicks = 0
        for action in actions:
            if deadline is not None and time.monotonic() >= deadline:
                write_auto_log(log_path, "loop timeout reached; exit=0")
                return 0

            ptype = action.get("type", "click")

            if ptype == "wait":
                wait_ms = action.get("ms", 0)
                if wait_ms > 0:
                    write_auto_log(log_path, f"wait action ms={wait_ms}")
                    sleep_until_deadline(wait_ms / 1000.0, deadline)
                continue

            if mode == "window":
                hwnd = action.get("hwnd")
                if not hwnd or not user32.IsWindow(hwnd):
                    active_windows = list_visible_windows()
                    title = action.get("win_title")
                    found_hwnd = next((h for h, t in active_windows if t == title), None)
                    if not found_hwnd and title:
                        found_hwnd = next((h for h, t in active_windows if title.lower() in t.lower()), None)
                    if found_hwnd:
                        hwnd = found_hwnd
                        action["hwnd"] = hwnd
                        write_auto_log(log_path, f"re-resolved window '{title}' to HWND {hwnd}")
                if hwnd and user32.IsWindow(hwnd):
                    if perform_window_mouse_action(hwnd, action):
                        clicks += 1
                        write_auto_log(log_path, f"ran window action type={ptype} title={action.get('win_title')} x={action.get('x')} y={action.get('y')}")
                    else:
                        write_auto_log(log_path, f"skipped window action outside client area type={ptype} title={action.get('win_title')} x={action.get('x')} y={action.get('y')}")
                else:
                    write_auto_log(log_path, f"missing window for action title={action.get('win_title')}")
            else:
                perform_screen_mouse_action(action)
                clicks += 1
                write_auto_log(log_path, f"ran screen action type={ptype} x={action.get('x')} y={action.get('y')}")

            delay_ms = action.get("delay") if action.get("delay") is not None else global_interval_ms
            if delay_ms > 0:
                sleep_until_deadline(delay_ms / 1000.0, deadline)
        rounds += 1
        write_auto_log(log_path, f"finished round {rounds}; clicks={clicks}")
        if not loop_enabled:
            write_auto_log(log_path, "loop disabled; exit=0")
            return 0
        if max_rounds > 0 and rounds >= max_rounds:
            write_auto_log(log_path, "max rounds reached; exit=0")
            return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Mouse Click Tool Minified")
    parser.add_argument("--auto", action="store_true", help="Run saved auto startup config")
    parser.add_argument("--silent", action="store_true", help="Suppress UI messages in automation mode")
    parser.add_argument("--config", help="Optional config path for --auto")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    exe_name = os.path.basename(sys.executable).lower()
    if args.silent and exe_name not in {"python.exe", "pythonw.exe"}:
        try:
            kernel32.FreeConsole()
        except (AttributeError, OSError):
            pass

    mutex_handle = acquire_single_instance_mutex()
    if mutex_handle is None:
        if not args.silent:
            show_already_running_message()
        return 4

    try:
        if args.auto:
            config_path = args.config or get_auto_config_path()
            log_path = get_auto_log_path()
            write_auto_log(log_path, f"process started; argv={argv if argv is not None else sys.argv[1:]}")
            result = run_auto_config(config_path, log_path)
            write_auto_log(log_path, f"process finished; exit={result}")
            return result

        ClickerApp().run()
        return 0
    finally:
        release_single_instance_mutex(mutex_handle)


if __name__ == "__main__":
    raise SystemExit(main())
