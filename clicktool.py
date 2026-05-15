import ctypes
from ctypes import wintypes
import argparse
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os
import sys
import time
from datetime import datetime

import win32gui
import win32api
import win32con

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

WH_MOUSE_LL = 14
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_RBUTTONDOWN = 0x0204
WM_RBUTTONUP = 0x0205
WM_MBUTTONDOWN = 0x0207
WM_MBUTTONUP = 0x0208
WM_MOUSEWHEEL = 0x020A
WM_XBUTTONDOWN = 0x020B
WM_XBUTTONUP = 0x020C
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
kernel32.CreateMutexW.restype = wintypes.HANDLE
kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.GetLastError.restype = wintypes.DWORD
kernel32.ReleaseMutex.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]


DOT_SIZE = 40
APP_NAME = "ClickTool"
AUTO_CONFIG_FILENAME = "auto_config.json"
DEFAULT_AUTO_LOOP_TIMEOUT_SECONDS = 60
DEFAULT_AUTO_LOOP_MAX_ROUNDS = 3
DEFAULT_TARGET_WAIT_SECONDS = 60
DEFAULT_PURE_BACKGROUND_WINDOW_CLICK = False
DEFAULT_INTERVAL_MS = 500
DEFAULT_WAIT_MS = 500
AUTO_LOG_DIRNAME = "logs"
ERROR_ALREADY_EXISTS = 183
WHEEL_DELTA = 120
XBUTTON1 = 0x0001
XBUTTON2 = 0x0002
MK_XBUTTON1 = 0x0020
MK_XBUTTON2 = 0x0040
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_XDOWN = 0x0080
MOUSEEVENTF_XUP = 0x0100
MOUSEEVENTF_WHEEL = 0x0800
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
    "left": (WM_LBUTTONDOWN, WM_LBUTTONUP, win32con.MK_LBUTTON, 0, 0),
    "right": (WM_RBUTTONDOWN, WM_RBUTTONUP, win32con.MK_RBUTTON, 0, 0),
    "middle": (WM_MBUTTONDOWN, WM_MBUTTONUP, win32con.MK_MBUTTON, 0, 0),
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
DEFAULT_HOTKEYS = {
    "start": "Ctrl+Enter",
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


def get_client_bounds_in_window(hwnd):
    rect = get_window_rect(hwnd)
    client_rect = get_client_rect(hwnd)
    if not rect or not client_rect:
        return None
    client_left, client_top = client_to_screen(hwnd, client_rect[0], client_rect[1])
    left = client_left - rect[0]
    top = client_top - rect[1]
    return (left, top, left + client_rect[2] - client_rect[0], top + client_rect[3] - client_rect[1])


def clamp_window_position(hwnd: int, x: int, y: int, pure_background: bool = False) -> tuple[int, int]:
    bounds = get_client_bounds_in_window(hwnd) if pure_background else None
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
    return os.path.join(log_dir, "auto.log")


def write_auto_log(log_path: str | None, message: str) -> None:
    if not log_path:
        return
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {message}\n")
    except Exception:
        pass


def read_script_file(file_path: str) -> dict:
    with open(file_path, "r", encoding="utf-8-sig") as f:
        data = json.load(f)
    normalize_script_data(data)
    return data


def write_script_file(file_path: str, data: dict) -> None:
    directory = os.path.dirname(file_path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def normalize_script_data(data: dict) -> dict:
    if "mode" not in data:
        data["mode"] = "window" if data.get("window_positions") else "screen"

    settings = data.setdefault("settings", {})
    settings["pure_background_window_click"] = bool(
        settings.get("pure_background_window_click", DEFAULT_PURE_BACKGROUND_WINDOW_CLICK)
    )
    settings["default_wait_ms"] = coerce_non_negative_int(
        settings.get("default_wait_ms"),
        DEFAULT_WAIT_MS,
    )
    hotkeys = settings.setdefault("hotkeys", {})
    for action, default in DEFAULT_HOTKEYS.items():
        hotkeys[action] = normalize_hotkey_text(hotkeys.get(action, default))

    auto = data.setdefault("auto", {})
    auto["loop_timeout_seconds"] = coerce_non_negative_int(
        auto.get("loop_timeout_seconds"),
        DEFAULT_AUTO_LOOP_TIMEOUT_SECONDS,
    )
    auto["loop_max_rounds"] = coerce_non_negative_int(
        auto.get("loop_max_rounds"),
        DEFAULT_AUTO_LOOP_MAX_ROUNDS,
    )
    auto["target_wait_seconds"] = coerce_non_negative_int(
        auto.get("target_wait_seconds"),
        DEFAULT_TARGET_WAIT_SECONDS,
    )

    for collection_name in ("screen_positions", "window_positions", "actions"):
        for action in data.get(collection_name, []):
            normalize_mouse_action(action)
    return data


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


def normalize_hotkey_text(value) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    text = text.strip("<>")
    text = text.replace("-", "+")
    parts = [part.strip() for part in text.split("+") if part.strip()]
    if not parts:
        return ""

    modifiers: list[str] = []
    key = ""
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


def canonical_key_name(key: str) -> str:
    if len(key) == 1:
        return key.upper()
    if key.lower().startswith("f") and key[1:].isdigit():
        return key.upper()
    return key[:1].upper() + key[1:]


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
    if action_type == "click":
        button = MOUSE_BUTTON_LABELS.get(action.get("button", "left"), "Left")
        return f"{prefix}{button} at ({int(action['x'])}, {int(action['y'])})"
    if action_type == "wheel":
        delta = coerce_wheel_delta(action.get("delta"), -1)
        return f"{prefix}Delta {delta} at ({int(action['x'])}, {int(action['y'])})"
    return f"Delay: {action['ms']}ms"


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
        if all(title in found for title in titles):
            if log_path:
                write_auto_log(log_path, f"matched windows: {sorted(found.keys())}")
            return found
        if log_path:
            missing = [title for title in titles if title not in found]
            found_titles = [title for title in titles if title in found]
            write_auto_log(log_path, f"waiting for windows; found={found_titles}; missing={missing}")
        if timeout_seconds <= 0 or time.monotonic() >= deadline:
            return found
        time.sleep(1)


def make_lparam(x: int, y: int) -> int:
    return ((int(y) & 0xFFFF) << 16) | (int(x) & 0xFFFF)


def make_wparam(low_word: int, high_word: int) -> int:
    return ((int(high_word) & 0xFFFF) << 16) | (int(low_word) & 0xFFFF)


def perform_screen_mouse_action(action: dict) -> bool:
    action_type = action.get("type", "click")
    x = int(action["x"])
    y = int(action["y"])
    win32api.SetCursorPos((x, y))

    if action_type == "click":
        button = action.get("button", "left")
        down_flag, up_flag, data = BUTTON_INPUT_MAP.get(button, BUTTON_INPUT_MAP["left"])
        win32api.mouse_event(down_flag, 0, 0, data, 0)
        time.sleep(0.05)
        win32api.mouse_event(up_flag, 0, 0, data, 0)
        return True

    if action_type == "wheel":
        delta = coerce_wheel_delta(action.get("delta"), -1)
        win32api.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, delta * WHEEL_DELTA, 0)
        return True

    return False


def post_window_mouse_action(target_hwnd: int, action: dict, client_x: int, client_y: int, screen_x: int, screen_y: int) -> bool:
    action_type = action.get("type", "click")
    if action_type == "click":
        button = action.get("button", "left")
        down_msg, up_msg, down_low_word, down_high_word, up_high_word = BUTTON_MESSAGE_MAP.get(
            button,
            BUTTON_MESSAGE_MAP["left"],
        )
        lparam = make_lparam(client_x, client_y)
        win32gui.PostMessage(target_hwnd, down_msg, make_wparam(down_low_word, down_high_word), lparam)
        win32gui.PostMessage(target_hwnd, up_msg, make_wparam(0, up_high_word), lparam)
        return True

    if action_type == "wheel":
        delta = coerce_wheel_delta(action.get("delta"), -1)
        win32gui.PostMessage(
            target_hwnd,
            WM_MOUSEWHEEL,
            make_wparam(0, delta * WHEEL_DELTA),
            make_lparam(screen_x, screen_y),
        )
        return True

    return False


def perform_window_mouse_action(hwnd: int, action: dict, pure_background: bool = False) -> bool:
    if not hwnd or not user32.IsWindow(hwnd):
        return False

    rect = get_window_rect(hwnd)
    if not rect:
        return False

    normalize_mouse_action(action)
    x = int(action["x"])
    y = int(action["y"])
    sx = int(rect[0] + x)
    sy = int(rect[1] + y)
    target_hwnd = hwnd
    best_area = (rect[2] - rect[0]) * (rect[3] - rect[1])

    def enum_cb(child_hwnd, lparam):
        nonlocal target_hwnd, best_area
        try:
            r = win32gui.GetWindowRect(child_hwnd)
            if r[0] <= sx < r[2] and r[1] <= sy < r[3]:
                area = (r[2] - r[0]) * (r[3] - r[1])
                if area <= best_area:
                    target_hwnd = child_hwnd
                    best_area = area
        except Exception:
            pass
        return True

    win32gui.EnumChildWindows(hwnd, enum_cb, None)

    t_cl_tl_sx, t_cl_tl_sy = win32gui.ClientToScreen(target_hwnd, (0, 0))
    tx = int(sx - t_cl_tl_sx)
    ty = int(sy - t_cl_tl_sy)

    t_cl_rect = RECT()
    user32.GetClientRect(target_hwnd, ctypes.byref(t_cl_rect))
    cw = t_cl_rect.right - t_cl_rect.left
    ch = t_cl_rect.bottom - t_cl_rect.top

    if 0 <= tx < cw and 0 <= ty < ch:
        return post_window_mouse_action(target_hwnd, action, tx, ty, sx, sy)

    if pure_background:
        return False

    try:
        win32gui.SetForegroundWindow(hwnd)
    except Exception:
        pass
    fallback_action = dict(action)
    fallback_action["x"] = sx
    fallback_action["y"] = sy
    return perform_screen_mouse_action(fallback_action)


def click_window_position(hwnd: int, x: int, y: int, pure_background: bool = False, button: str = "left") -> bool:
    return perform_window_mouse_action(
        hwnd,
        {"type": "click", "x": x, "y": y, "button": button},
        pure_background,
    )


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


def run_auto_config(config_path: str, log_path: str | None = None) -> int:
    write_auto_log(log_path, f"auto run started; config={config_path}")
    if not os.path.exists(config_path):
        write_auto_log(log_path, "auto config not found; exit=2")
        return 2

    try:
        data = read_script_file(config_path)
    except Exception as e:
        write_auto_log(log_path, f"failed to read auto config: {e}; exit=2")
        return 2

    mode = data.get("mode", "window" if data.get("window_positions") else "screen")
    loop_enabled = bool(data.get("loop", True))
    global_interval_ms = coerce_non_negative_int(data.get("global_interval"), 500)
    settings = data.get("settings", {})
    pure_background = bool(settings.get("pure_background_window_click", DEFAULT_PURE_BACKGROUND_WINDOW_CLICK))
    auto = data.get("auto", {})
    timeout_seconds = coerce_non_negative_int(
        auto.get("loop_timeout_seconds"),
        DEFAULT_AUTO_LOOP_TIMEOUT_SECONDS,
    )
    max_rounds = coerce_non_negative_int(
        auto.get("loop_max_rounds"),
        DEFAULT_AUTO_LOOP_MAX_ROUNDS,
    )
    target_wait_seconds = coerce_non_negative_int(
        auto.get("target_wait_seconds"),
        DEFAULT_TARGET_WAIT_SECONDS,
    )

    if loop_enabled and timeout_seconds == 0 and max_rounds == 0:
        timeout_seconds = DEFAULT_AUTO_LOOP_TIMEOUT_SECONDS
        max_rounds = DEFAULT_AUTO_LOOP_MAX_ROUNDS

    write_auto_log(
        log_path,
        f"loaded auto config; mode={mode}; loop={loop_enabled}; pure_background={pure_background}; "
        f"timeouts={{loop:{timeout_seconds}, rounds:{max_rounds}, wait:{target_wait_seconds}}}",
    )
    write_auto_log(log_path, f"target windows={data.get('target_windows', [])}")
    write_auto_log(log_path, f"action count={len(data.get('actions', []))}")

    positions: list[dict] = []
    if mode == "window":
        titles = set(data.get("target_windows", []))
        titles.update(p.get("win_title") for p in data.get("window_positions", []) if p.get("win_title"))
        titles = sorted(titles)
        write_auto_log(log_path, f"waiting for windows={titles}")
        window_map = wait_for_windows(titles, target_wait_seconds, log_path)
        write_auto_log(log_path, f"window map keys={sorted(window_map.keys())}")

        if mode == "window" and not window_map:
            write_auto_log(log_path, "no target windows matched before timeout")

        if mode == "window" and window_map:
            write_auto_log(log_path, f"matched window titles={list(window_map.keys())}")


        for p in data.get("window_positions", []):
            hwnd = window_map.get(p.get("win_title"))
            if hwnd and is_position_action(p):
                positions.append({
                    "type": p.get("type", "click"),
                    "x": p["x"],
                    "y": p["y"],
                    "button": p.get("button"),
                    "delta": p.get("delta"),
                    "delay": p.get("delay"),
                    "hwnd": hwnd,
                })
    else:
        for p in data.get("screen_positions", []):
            if is_position_action(p):
                positions.append({
                    "type": p.get("type", "click"),
                    "x": p["x"],
                    "y": p["y"],
                    "button": p.get("button"),
                    "delta": p.get("delta"),
                    "delay": p.get("delay"),
                })

    if not positions:
        write_auto_log(log_path, "no runnable positions resolved; exit=3")
        return 3

    write_auto_log(log_path, f"resolved runnable positions={len(positions)}")

    deadline = None
    if loop_enabled and timeout_seconds > 0:
        deadline = time.monotonic() + timeout_seconds

    rounds = 0
    while True:
        write_auto_log(log_path, f"starting round {rounds + 1}")
        round_clicks = 0
        round_waits = 0

        for action in data.get("actions", []):
            if deadline is not None and time.monotonic() >= deadline:
                write_auto_log(log_path, "loop timeout reached before action; exit=0")
                return 0

            normalize_mouse_action(action)
            action_type = action.get("type", "click")
            if is_position_action(action):
                if mode == "window":
                    hwnd = window_map.get(action.get("win_title"))
                    if hwnd:
                        if perform_window_mouse_action(hwnd, action, pure_background):
                            round_clicks += 1
                            write_auto_log(log_path, f"ran window action type={action_type} title={action.get('win_title')} x={action.get('x')} y={action.get('y')}")
                        else:
                            write_auto_log(log_path, f"skipped window action type={action_type} title={action.get('win_title')} x={action.get('x')} y={action.get('y')}; pure_background={pure_background}")
                    else:
                        write_auto_log(log_path, f"missing window for action title={action.get('win_title')}")
                else:
                    perform_screen_mouse_action(action)
                    round_clicks += 1
                    write_auto_log(log_path, f"ran screen action type={action_type} x={action.get('x')} y={action.get('y')}")

                # Implicit wait if global_interval is set and no specific delay in action
                # However, the new system prefers explicit wait items.
                # To maintain compatibility with older scripts that might be normalized:
                delay_ms = action.get("delay")
                if delay_ms is None:
                    delay_ms = global_interval_ms
                if delay_ms > 0:
                    sleep_until_deadline(delay_ms / 1000.0, deadline)

            elif action_type == "wait":
                wait_ms = action.get("ms", 0)
                if wait_ms > 0:
                    round_waits += 1
                    write_auto_log(log_path, f"wait action ms={wait_ms}")
                    sleep_until_deadline(wait_ms / 1000.0, deadline)

        rounds += 1
        write_auto_log(log_path, f"finished round {rounds}; clicks={round_clicks}; waits={round_waits}")
        if not loop_enabled:
            write_auto_log(log_path, "loop disabled; exit=0")
            return 0
        if max_rounds > 0 and rounds >= max_rounds:
            write_auto_log(log_path, f"max rounds reached ({max_rounds}); exit=0")
            return 0
        if deadline is not None and time.monotonic() >= deadline:
            write_auto_log(log_path, "loop timeout reached after round; exit=0")
            return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Mouse Click Tool")
    parser.add_argument("--auto", action="store_true", help="Run the saved auto startup config.")
    parser.add_argument("--silent", action="store_true", help="Suppress UI messages in automation mode.")
    parser.add_argument("--config", help="Optional config path for --auto. Defaults to the saved auto config.")
    return parser.parse_args(argv)


def show_already_running_message() -> None:
    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo("Already Running", "Click Tool is already running.")
    root.destroy()


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

class DraggableDot(tk.Toplevel):
    """A semi-transparent, numbered, draggable dot that stays on top."""
    def __init__(self, master, index, x, y, on_move, on_click=None, hwnd=None, pure_background=False):
        super().__init__(master)
        self.index = index  # 0-based index
        self.on_move = on_move
        self.on_click = on_click
        self.hwnd = hwnd # If set, x and y are relative to this window's top-left
        self.pure_background = pure_background

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
                rel_x = new_screen_x - rect[0]
                rel_y = new_screen_y - rect[1]
                rel_x, rel_y = clamp_window_position(self.hwnd, rel_x, rel_y, self.pure_background)
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
        self.mouse_button_var = tk.StringVar(value="left")
        self.loop_var = tk.BooleanVar(value=True)
        self.pure_background_window_click_var = tk.BooleanVar(value=DEFAULT_PURE_BACKGROUND_WINDOW_CLICK)
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
        self._set_button_controls_enabled(False)
        self._apply_hotkeys(show_status=False)
        self.root.bind_all("<KeyPress>", self._on_key_press, add="+")
        self.sync_dots_loop()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_ui(self) -> None:
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
        self.start_button = ttk.Button(run_frame, text="Start", command=self.start_clicking, width=8)
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
        bg_frame = ttk.LabelFrame(frame, text="Window Mode", padding=10)
        bg_frame.grid(row=0, column=0, sticky="ew")
        ttk.Checkbutton(
            bg_frame,
            text="Pure background clicking",
            variable=self.pure_background_window_click_var,
            command=self._on_pure_background_setting_changed,
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            bg_frame,
            text="When enabled, window-mode dots are limited to the target client area and title-bar clicks are disabled.",
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
        frame.rowconfigure(1, weight=1)
        # Row 1: Position List Label
        ttk.Label(frame, text="Click Order & Positions").grid(
            row=0, column=0, sticky="w", pady=(0, 4)
        )

        # Row 2: Treeview for Actions
        list_frame = ttk.Frame(frame)
        list_frame.grid(row=1, column=0, sticky="nsew")
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        columns = ("#", "type", "details")
        self.screen_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=9)
        self.screen_tree.heading("#", text="#")
        self.screen_tree.heading("type", text="Action")
        self.screen_tree.heading("details", text="Details")
        self.screen_tree.column("#", width=40, anchor="center")
        self.screen_tree.column("type", width=100, anchor="center")
        self.screen_tree.column("details", width=360, anchor="w")
        
        self.screen_tree.grid(row=0, column=0, sticky="nsew")
        self.screen_tree.bind("<<TreeviewSelect>>", self._on_screen_list_select)
        
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.screen_tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.screen_tree.configure(yscrollcommand=scrollbar.set)

        # Row 3: Selected Item Properties
        prop_frame = ttk.LabelFrame(frame, text="Selected Item Properties", padding=8)
        prop_frame.grid(row=2, column=0, sticky="ew", pady=(8, 0))
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
        ttk.Label(
            prop_frame,
            text="Click: x,y + button; Wheel: x,y,delta; Wait: ms",
            font=("", 8),
            foreground="#666666",
        ).grid(row=2, column=0, columnspan=3, sticky="w")

        # Row 4: Controls
        action_bar = ttk.Frame(frame)
        action_bar.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        add_group = ttk.LabelFrame(action_bar, text="Add", padding=(6, 4))
        add_group.pack(side="left", padx=(0, 8))
        ttk.Button(add_group, text="Dot", command=self.add_screen_dot, width=9).pack(side="left", padx=(0, 4))
        ttk.Button(add_group, text="Wheel", command=self.add_screen_wheel, width=9).pack(side="left", padx=(0, 4))
        ttk.Button(add_group, text="Wait", command=self.add_screen_wait, width=9).pack(side="left")

        edit_group = ttk.LabelFrame(action_bar, text="Edit", padding=(6, 4))
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
        
        self.target_win_list = tk.Listbox(win_list_frame, height=12, width=28)
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
        
        columns = ("#", "type", "details")
        self.window_pt_tree = ttk.Treeview(pt_list_frame, columns=columns, show="headings", height=12)
        self.window_pt_tree.heading("#", text="#")
        self.window_pt_tree.heading("type", text="Action")
        self.window_pt_tree.heading("details", text="Details")
        self.window_pt_tree.column("#", width=40, anchor="center")
        self.window_pt_tree.column("type", width=80, anchor="center")
        self.window_pt_tree.column("details", width=330, anchor="w")
        
        self.window_pt_tree.pack(side="left", fill="both", expand=True)
        self.window_pt_tree.bind("<<TreeviewSelect>>", self._on_window_list_select)
        
        pt_scroll = ttk.Scrollbar(pt_list_frame, orient="vertical", command=self.window_pt_tree.yview)
        pt_scroll.pack(side="right", fill="y")
        self.window_pt_tree.configure(yscrollcommand=pt_scroll.set)
        
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
        ttk.Label(
            win_prop_frame,
            text="Click: x,y + button; Wheel: x,y,delta; Wait: ms",
            font=("", 8),
            foreground="#666666",
        ).grid(row=2, column=0, columnspan=3, sticky="w")

    def _on_tab_changed(self, event):
        """Show only the dots belonging to the active tab."""
        # If clicking is active, dots are already hidden
        if self._click_thread and self._click_thread.is_alive():
            return
            
        current_tab = self.notebook.index(self.notebook.select())
        if current_tab == 0: # Screen
            self._active_mode = "screen"
            for p in self._screen_positions:
                if is_position_action(p): p["dot"].deiconify()
            for p in self._window_positions:
                if is_position_action(p): p["dot"].withdraw()
        elif current_tab == 1: # Window
            self._active_mode = "window"
            for p in self._screen_positions:
                if is_position_action(p): p["dot"].withdraw()
            for p in self._window_positions:
                if is_position_action(p): p["dot"].deiconify()
        else:
            self._set_dots_visible(False)
            
    def sync_dots_loop(self):
        """Update window-based dots to follow their windows and prevent overflow."""
        # Only sync if we are not clicking
        is_clicking = self._click_thread and self._click_thread.is_alive()
        current_tab = self.notebook.index(self.notebook.select())
        
        if current_tab == 1 and not is_clicking:
            for p in self._window_positions:
                if not is_position_action(p):
                    continue
                hwnd = p.get("hwnd")
                if hwnd and user32.IsWindow(hwnd):
                    if user32.IsIconic(hwnd):
                        p["dot"].withdraw()
                    else:
                        rect = get_window_rect(hwnd)
                        if rect:
                            p["x"], p["y"] = clamp_window_position(
                                hwnd, p["x"], p["y"], self.pure_background_window_click_var.get()
                            )
                            p["dot"].pure_background = self.pure_background_window_click_var.get()

                            sx = rect[0] + p["x"]
                            sy = rect[1] + p["y"]
                            p["dot"].deiconify()
                            p["dot"].update_position(sx, sy)
                        else:
                            p["dot"].withdraw()
                else:
                    p["dot"].withdraw()
        
        self.root.after(100, self.sync_dots_loop)

    def _set_button_controls_enabled(self, enabled: bool) -> None:
        state = "readonly" if enabled else "disabled"
        for control in self._button_controls:
            control.config(state=state)

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
            self.add_window_dot()
        else:
            self.notebook.select(0)
            self.add_screen_dot()

    def add_current_wheel(self) -> None:
        if self._active_mode == "window":
            self.notebook.select(1)
            self.add_window_wheel()
        else:
            self.notebook.select(0)
            self.add_screen_wheel()

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

    def _on_mouse_button_selected(self, event=None) -> None:
        current_tab = self.notebook.index(self.notebook.select())
        editing_screen = current_tab == 0 or (current_tab == 2 and self._active_mode == "screen")
        tree = self.screen_tree if editing_screen else self.window_pt_tree
        positions = self._screen_positions if editing_screen else self._window_positions
        sel = tree.selection()
        if not sel:
            return

        index = tree.index(sel[0])
        if positions[index].get("type") != "click":
            return

        button = self.mouse_button_var.get()
        positions[index]["button"] = button if button in MOUSE_BUTTONS else "left"
        if editing_screen:
            self._refresh_screen_list_item(index)
        else:
            self._refresh_window_pt_item(index)

    def add_target_window(self):
        """Open a dialog to select a window from all visible windows."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Select Window (Auto-refreshing)")
        dialog.geometry("460x420")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Select a window from the list:").pack(anchor="w", padx=10, pady=(8, 4))

        list_frame = ttk.Frame(dialog)
        list_frame.pack(fill="both", expand=True, padx=10)
        
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
            "type": "click",
            "x": x,
            "y": y,
            "button": "left",
            "delay": None,
            "dot": dot
        })
        self._refresh_screen_list()
        # Select the newly added dot
        last_item = self.screen_tree.get_children()[-1]
        self.screen_tree.selection_set(last_item)
        self.screen_tree.see(last_item)
        self._on_screen_list_select()
        self.status_var.set(f"Added screen dot at center.")

    def add_screen_wheel(self) -> None:
        """Create a wheel action at the center of the screen."""
        screen_w = user32.GetSystemMetrics(0)
        screen_h = user32.GetSystemMetrics(1)
        x, y = screen_w // 2, screen_h // 2

        index = len(self._screen_positions)
        dot = DraggableDot(
            self.root,
            index,
            x,
            y,
            self._on_screen_dot_move,
            on_click=self._on_screen_dot_click,
        )

        self._screen_positions.append({
            "type": "wheel",
            "x": x,
            "y": y,
            "delta": -1,
            "delay": None,
            "dot": dot,
        })
        self._refresh_screen_list()
        last_item = self.screen_tree.get_children()[-1]
        self.screen_tree.selection_set(last_item)
        self.screen_tree.see(last_item)
        self._on_screen_list_select()
        self.status_var.set("Added screen wheel action at center.")

    def add_screen_wait(self) -> None:
        """Add a wait item to the screen list."""
        wait_ms = self._get_default_wait_ms()
        if wait_ms is None:
            return
        self._screen_positions.append({
            "type": "wait",
            "ms": wait_ms
        })
        self._refresh_screen_list()
        last_item = self.screen_tree.get_children()[-1]
        self.screen_tree.selection_set(last_item)
        self.screen_tree.see(last_item)
        self._on_screen_list_select()
        self.status_var.set(f"Added {wait_ms}ms wait.")

    def _on_screen_dot_click(self, index):
        """Select corresponding item in tree when dot is clicked."""
        self.notebook.select(0)
        items = self.screen_tree.get_children()
        if index < len(items):
            self.screen_tree.selection_set(items[index])
            self.screen_tree.see(items[index])
            self._on_screen_list_select()

    def _on_screen_dot_move(self, index, x, y):
        """Callback when a screen dot is dragged."""
        self._screen_positions[index]["x"] = x
        self._screen_positions[index]["y"] = y
        self._refresh_screen_list_item(index)

    def _on_screen_list_select(self, event=None):
        """Update the property fields when a position is selected in the screen tree."""
        sel = self.screen_tree.selection()
        if not sel:
            return
        index = self.screen_tree.index(sel[0])
        pos = self._screen_positions[index]
        if pos["type"] == "click":
            self.screen_prop_label.config(text="Pos (x,y):")
            self.step_delay_var.set(f"{int(pos['x'])},{int(pos['y'])}")
            self.mouse_button_var.set(pos.get("button", "left"))
            self._set_button_controls_enabled(True)
        elif pos["type"] == "wheel":
            self.screen_prop_label.config(text="Wheel (x,y,delta):")
            self.step_delay_var.set(f"{int(pos['x'])},{int(pos['y'])},{coerce_wheel_delta(pos.get('delta'), -1)}")
            self._set_button_controls_enabled(False)
        else:
            self.screen_prop_label.config(text="Wait (ms):")
            self.step_delay_var.set(str(pos["ms"]))
            self._set_button_controls_enabled(False)

    def remove_screen_position(self) -> None:
        sel = self.screen_tree.selection()
        if not sel:
            return
        index = self.screen_tree.index(sel[0])
        if is_position_action(self._screen_positions[index]):
            self._screen_positions[index]["dot"].destroy()
        del self._screen_positions[index]
        self._refresh_screen_list()

    def move_screen_position(self, delta: int) -> None:
        sel = self.screen_tree.selection()
        if not sel:
            return
        index = self.screen_tree.index(sel[0])
        target = index + delta
        if not 0 <= target < len(self._screen_positions):
            return
            
        self._screen_positions[index], self._screen_positions[target] = (
            self._screen_positions[target],
            self._screen_positions[index],
        )
        self._refresh_screen_list()
        new_items = self.screen_tree.get_children()
        self.screen_tree.selection_set(new_items[target])
        self.screen_tree.see(new_items[target])
        self._on_screen_list_select()

    def _refresh_screen_list(self) -> None:
        for item in self.screen_tree.get_children():
            self.screen_tree.delete(item)

        dot_count = 0
        for i, item in enumerate(self._screen_positions):
            if is_position_action(item):
                dot_count += 1
                item["dot"].index = i
                item["dot"].set_number(dot_count)
                self.screen_tree.insert(
                    "",
                    "end",
                    values=(dot_count, get_mouse_action_name(item), get_mouse_action_details(item)),
                )
            else:
                details = f"Delay: {item['ms']}ms"
                self.screen_tree.insert("", "end", values=("", "Wait", details))

    def _refresh_screen_list_item(self, index: int) -> None:
        self._refresh_screen_list()
        items = self.screen_tree.get_children()
        if 0 <= index < len(items):
            self.screen_tree.selection_set(items[index])
            self.screen_tree.see(items[index])

    def clear_screen_positions(self) -> None:
        for p in self._screen_positions:
            if is_position_action(p):
                p["dot"].destroy()
        self._screen_positions.clear()
        self._refresh_screen_list()

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
            
        win_w = rect[2] - rect[0]
        win_h = rect[3] - rect[1]
        rel_x, rel_y = win_w // 2, win_h // 2
        if self.pure_background_window_click_var.get():
            bounds = get_client_bounds_in_window(hwnd)
            if bounds:
                rel_x = (bounds[0] + bounds[2]) // 2
                rel_y = (bounds[1] + bounds[3]) // 2

        index = len(self._window_positions)
        dot = DraggableDot(self.root, index, rel_x, rel_y, self._on_window_dot_move,
                          on_click=self._on_window_dot_click, hwnd=hwnd,
                          pure_background=self.pure_background_window_click_var.get())
        
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
        last_item = self.window_pt_tree.get_children()[-1]
        self.window_pt_tree.selection_set(last_item)
        self.window_pt_tree.see(last_item)
        
        self.status_var.set(f"Added window dot for '{win_data['title']}'.")

    def add_window_wheel(self) -> None:
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
        rel_x, rel_y = win_w // 2, win_h // 2
        if self.pure_background_window_click_var.get():
            bounds = get_client_bounds_in_window(hwnd)
            if bounds:
                rel_x = (bounds[0] + bounds[2]) // 2
                rel_y = (bounds[1] + bounds[3]) // 2

        index = len(self._window_positions)
        dot = DraggableDot(
            self.root,
            index,
            rel_x,
            rel_y,
            self._on_window_dot_move,
            on_click=self._on_window_dot_click,
            hwnd=hwnd,
            pure_background=self.pure_background_window_click_var.get(),
        )

        self._window_positions.append({
            "type": "wheel",
            "x": rel_x,
            "y": rel_y,
            "delta": -1,
            "delay": None,
            "dot": dot,
            "hwnd": hwnd,
            "win_title": win_data["title"],
        })
        self._refresh_window_pt_list()
        last_item = self.window_pt_tree.get_children()[-1]
        self.window_pt_tree.selection_set(last_item)
        self.window_pt_tree.see(last_item)
        self._on_window_list_select()

        self.status_var.set(f"Added window wheel action for '{win_data['title']}'.")

    def add_window_wait(self) -> None:
        """Add a wait item to the window list."""
        wait_ms = self._get_default_wait_ms()
        if wait_ms is None:
            return
        self._window_positions.append({
            "type": "wait",
            "ms": wait_ms
        })
        self._refresh_window_pt_list()
        last_item = self.window_pt_tree.get_children()[-1]
        self.window_pt_tree.selection_set(last_item)
        self.window_pt_tree.see(last_item)
        self._on_window_list_select()
        self.status_var.set(f"Added {wait_ms}ms wait.")

    def _on_window_dot_click(self, index):
        """Select corresponding item in tree when dot is clicked."""
        self.notebook.select(1)
        items = self.window_pt_tree.get_children()
        if index < len(items):
            self.window_pt_tree.selection_set(items[index])
            self.window_pt_tree.see(items[index])
            self._on_window_list_select()

    def _on_window_dot_move(self, index, x, y):
        """Callback when a window dot is dragged (x, y are relative)."""
        self._window_positions[index]["x"] = x
        self._window_positions[index]["y"] = y
        self._refresh_window_pt_item(index)

    def _on_window_list_select(self, event=None):
        """Update the property fields when a position is selected in the window point tree."""
        sel = self.window_pt_tree.selection()
        if not sel:
            return
        index = self.window_pt_tree.index(sel[0])
        pos = self._window_positions[index]
        if pos["type"] == "click":
            self.window_prop_label.config(text="Pos (x,y):")
            self.step_delay_var.set(f"{int(pos['x'])},{int(pos['y'])}")
            self.mouse_button_var.set(pos.get("button", "left"))
            self._set_button_controls_enabled(True)
        elif pos["type"] == "wheel":
            self.window_prop_label.config(text="Wheel (x,y,delta):")
            self.step_delay_var.set(f"{int(pos['x'])},{int(pos['y'])},{coerce_wheel_delta(pos.get('delta'), -1)}")
            self._set_button_controls_enabled(False)
        else:
            self.window_prop_label.config(text="Wait (ms):")
            self.step_delay_var.set(str(pos["ms"]))
            self._set_button_controls_enabled(False)

    def remove_window_position(self) -> None:
        sel = self.window_pt_tree.selection()
        if not sel:
            return
        index = self.window_pt_tree.index(sel[0])
        if is_position_action(self._window_positions[index]):
            self._window_positions[index]["dot"].destroy()
        del self._window_positions[index]
        self._refresh_window_pt_list()

    def move_window_position(self, delta: int) -> None:
        sel = self.window_pt_tree.selection()
        if not sel:
            return
        index = self.window_pt_tree.index(sel[0])
        target = index + delta
        if not 0 <= target < len(self._window_positions):
            return
            
        self._window_positions[index], self._window_positions[target] = (
            self._window_positions[target],
            self._window_positions[index],
        )
        self._refresh_window_pt_list()
        new_items = self.window_pt_tree.get_children()
        self.window_pt_tree.selection_set(new_items[target])
        self.window_pt_tree.see(new_items[target])
        self._on_window_list_select()

    def _refresh_window_pt_list(self) -> None:
        for item in self.window_pt_tree.get_children():
            self.window_pt_tree.delete(item)

        dot_count = 0
        for i, item in enumerate(self._window_positions):
            if is_position_action(item):
                dot_count += 1
                item["dot"].index = i
                item["dot"].set_number(dot_count)
                title = (item['win_title'][:15] + '..') if len(item['win_title']) > 15 else item['win_title']
                details = get_mouse_action_details(item, title)
                self.window_pt_tree.insert("", "end", values=(dot_count, get_mouse_action_name(item), details))
            else:
                details = f"Delay: {item['ms']}ms"
                self.window_pt_tree.insert("", "end", values=("", "Wait", details))

    def _refresh_window_pt_item(self, index: int) -> None:
        self._refresh_window_pt_list()
        items = self.window_pt_tree.get_children()
        if 0 <= index < len(items):
            self.window_pt_tree.selection_set(items[index])
            self.window_pt_tree.see(items[index])

    def clear_window_positions(self) -> None:
        for p in self._window_positions:
            if is_position_action(p):
                p["dot"].destroy()
        self._window_positions.clear()
        self._refresh_window_pt_list()

    def apply_step_delay(self):
        """Save the custom delay for the selected position in either mode."""
        current_tab = self.notebook.index(self.notebook.select())
        editing_screen = current_tab == 0 or (current_tab == 2 and self._active_mode == "screen")
        if editing_screen:
            sel = self.screen_tree.selection()
            positions = self._screen_positions
        else:
            sel = self.window_pt_tree.selection()
            positions = self._window_positions
            
        if not sel:
            messagebox.showinfo("Selection Required", "Select a position first.")
            return
        
        val = self.step_delay_var.get().strip()
        index = self.screen_tree.index(sel[0]) if editing_screen else self.window_pt_tree.index(sel[0])
        if not val:
            if positions[index]["type"] == "click":
                pass # Can't clear pos via delay entry easily
            elif positions[index]["type"] == "wheel":
                pass
            else:
                positions[index]["ms"] = 0
        else:
            try:
                if positions[index]["type"] == "click":
                    parts = val.split(',')
                    if len(parts) == 2:
                        positions[index]["x"] = int(parts[0])
                        positions[index]["y"] = int(parts[1])
                    positions[index]["button"] = (
                        self.mouse_button_var.get()
                        if self.mouse_button_var.get() in MOUSE_BUTTONS
                        else "left"
                    )
                elif positions[index]["type"] == "wheel":
                    parts = [p.strip() for p in val.split(',')]
                    if len(parts) == 1:
                        positions[index]["delta"] = coerce_wheel_delta(parts[0], -1)
                    elif len(parts) == 3:
                        positions[index]["x"] = int(parts[0])
                        positions[index]["y"] = int(parts[1])
                        positions[index]["delta"] = coerce_wheel_delta(parts[2], -1)
                    else:
                        raise ValueError
                else:
                    ms = int(val)
                    if ms < 0: raise ValueError
                    positions[index]["ms"] = ms
            except ValueError:
                messagebox.showerror("Invalid Value", "Enter ms, x,y for click, or x,y,delta for wheel.")
                return
        
        if editing_screen: self._refresh_screen_list()
        else: self._refresh_window_pt_list()
        self.status_var.set(f"Updated item {index+1}.")
        # Select back the item to keep focus
        new_items = (self.screen_tree if editing_screen else self.window_pt_tree).get_children()
        (self.screen_tree if editing_screen else self.window_pt_tree).selection_set(new_items[index])

    def _on_pure_background_setting_changed(self) -> None:
        enabled = self.pure_background_window_click_var.get()
        for p in self._window_positions:
            if not is_position_action(p):
                continue
            hwnd = p.get("hwnd")
            if hwnd and user32.IsWindow(hwnd):
                p["x"], p["y"] = clamp_window_position(hwnd, p["x"], p["y"], enabled)
            p["dot"].pure_background = enabled
        self._refresh_window_pt_list()
        self.status_var.set("Pure background window clicking is " + ("enabled." if enabled else "disabled."))

    def collect_script_data(self) -> dict:
        """Return the current GUI state in the script JSON format."""
        mode = self._active_mode

        def serialize_action(action: dict, include_window: bool = False) -> dict:
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
                    "ms": action.get("ms", 500),
                }
            if include_window:
                data["win_title"] = action.get("win_title")
            return data

        active_positions = self._screen_positions if mode == "screen" else self._window_positions
        return normalize_script_data({
            "mode": mode,
            "global_interval": self.interval_var.get(),
            "loop": self.loop_var.get(),
            "settings": {
                "pure_background_window_click": self.pure_background_window_click_var.get(),
                "default_wait_ms": coerce_non_negative_int(self.default_wait_var.get(), DEFAULT_WAIT_MS),
                "hotkeys": {
                    action: normalize_hotkey_text(var.get())
                    for action, var in self.hotkey_vars.items()
                },
            },
            "screen_positions": [serialize_action(p) for p in self._screen_positions],
            "target_windows": [w["title"] for w in self._target_windows],
            "window_positions": [serialize_action(p, include_window=True) for p in self._window_positions],
            # Unified action list for execution
            "actions": [serialize_action(p, include_window=(mode == "window")) for p in active_positions]
        })

    def apply_script_data(self, data: dict, source_path: str | None = None, show_warnings: bool = True) -> None:
        """Load script JSON data into the GUI."""
        normalize_script_data(data)

        self.clear_screen_positions()
        self.clear_window_positions()
        self._target_windows.clear()

        self.interval_var.set(data.get("global_interval", "500"))
        self.loop_var.set(data.get("loop", True))
        settings = data.get("settings", {})
        self.pure_background_window_click_var.set(
            settings.get("pure_background_window_click", DEFAULT_PURE_BACKGROUND_WINDOW_CLICK)
        )
        self.default_wait_var.set(str(settings.get("default_wait_ms", DEFAULT_WAIT_MS)))
        hotkeys = settings.get("hotkeys", {})
        for action, default in DEFAULT_HOTKEYS.items():
            self.hotkey_vars[action].set(hotkeys.get(action, default))
        self._apply_hotkeys(show_status=False)

        mode = data.get("mode", "window" if data.get("window_positions") else "screen")
        self.notebook.select(0 if mode == "screen" else 1)

        for p_data in data.get("screen_positions", []):
            normalize_mouse_action(p_data)
            if is_position_action(p_data):
                idx = len(self._screen_positions)
                dot = DraggableDot(
                    self.root,
                    idx,
                    p_data["x"],
                    p_data["y"],
                    self._on_screen_dot_move,
                    on_click=self._on_screen_dot_click,
                )
                action = {
                    "type": p_data.get("type", "click"),
                    "x": p_data["x"],
                    "y": p_data["y"],
                    "delay": p_data.get("delay"),
                    "dot": dot,
                }
                if action["type"] == "click":
                    action["button"] = p_data.get("button", "left")
                else:
                    action["delta"] = coerce_wheel_delta(p_data.get("delta"), -1)
                self._screen_positions.append(action)
            else:
                self._screen_positions.append({
                    "type": "wait",
                    "ms": p_data.get("ms", 500)
                })
        self._refresh_screen_list()

        active_windows = list_visible_windows()
        missing_windows = []
        for win_title in data.get("target_windows", []):
            found_hwnd = next((h for h, t in active_windows if t == win_title), None)
            if found_hwnd:
                self._target_windows.append({"hwnd": found_hwnd, "title": win_title})
            else:
                missing_windows.append(win_title)

        self._refresh_window_list()

        for p_data in data.get("window_positions", []):
            normalize_mouse_action(p_data)
            if is_position_action(p_data):
                win_title = p_data["win_title"]
                found_hwnd = next((w["hwnd"] for w in self._target_windows if w["title"] == win_title), None)
                idx = len(self._window_positions)
                dot = DraggableDot(
                    self.root,
                    idx,
                    p_data["x"],
                    p_data["y"],
                    self._on_window_dot_move,
                    on_click=self._on_window_dot_click,
                    hwnd=found_hwnd,
                    pure_background=self.pure_background_window_click_var.get(),
                )
                action = {
                    "type": p_data.get("type", "click"),
                    "x": p_data["x"],
                    "y": p_data["y"],
                    "delay": p_data.get("delay"),
                    "dot": dot,
                    "hwnd": found_hwnd,
                    "win_title": win_title,
                }
                if action["type"] == "click":
                    action["button"] = p_data.get("button", "left")
                else:
                    action["delta"] = coerce_wheel_delta(p_data.get("delta"), -1)
                self._window_positions.append(action)
            else:
                self._window_positions.append({
                    "type": "wait",
                    "ms": p_data.get("ms", 500)
                })
        self._refresh_window_pt_list()
        self._on_tab_changed(None)

        if missing_windows and show_warnings:
            messagebox.showwarning(
                "Missing Windows",
                "The following windows could not be found and their points may not work correctly:\n\n" +
                "\n".join(missing_windows),
            )

        if source_path:
            self.status_var.set(f"Imported script from {source_path}")

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
        timeout_entry = ttk.Entry(frame, textvariable=self.auto_loop_timeout_var, width=10)
        timeout_entry.grid(row=2, column=1, sticky="w", padx=(8, 0))

        ttk.Label(frame, text="Max loop rounds").grid(row=3, column=0, sticky="w", pady=(8, 0))
        rounds_entry = ttk.Entry(frame, textvariable=self.auto_loop_max_rounds_var, width=10)
        rounds_entry.grid(row=3, column=1, sticky="w", padx=(8, 0), pady=(8, 0))

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

        def save_current_to_auto() -> None:
            save_data_to_auto(self.collect_script_data(), "Current setup saved as auto config.")

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
        ttk.Button(button_row, text="Save Current", command=save_current_to_auto).pack(side="left", padx=(6, 0))
        ttk.Button(button_row, text="Clear", command=clear_auto_config).pack(side="left", padx=(6, 0))
        ttk.Button(button_row, text="Close", command=dialog.destroy).pack(side="right", padx=(20, 0))

        ttk.Label(frame, textvariable=status_var, foreground="#005a9e").grid(
            row=5,
            column=0,
            columnspan=3,
            sticky="w",
            pady=(12, 0),
        )

    def start_clicking(self) -> None:
        if self._click_thread and self._click_thread.is_alive():
            return
            
        mode = self._active_mode
        if mode == "screen":
            positions = self._screen_positions
        else:
            positions = self._window_positions
            
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
        
        # Snapshot actions for the thread
        actions_snapshot = []
        for p in positions:
            snapshot = {k: v for k, v in p.items() if k != "dot"}
            actions_snapshot.append(snapshot)
            
        # Hide dots while clicking to avoid blocking
        self._set_dots_visible(False)
        
        pure_background = self.pure_background_window_click_var.get()
        self._click_thread = threading.Thread(
            target=self._click_loop, args=(global_interval, actions_snapshot, mode, pure_background), daemon=True
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
            if is_position_action(p):
                if visible: p["dot"].deiconify()
                else: p["dot"].withdraw()
        for p in self._window_positions:
            if is_position_action(p):
                if visible: p["dot"].deiconify()
                else: p["dot"].withdraw()

    def _watch_escape(self) -> None:
        while not self._stop_event.wait(0.03):
            if user32.GetAsyncKeyState(VK_ESCAPE) & 0x8000:
                self._stop_event.set()
                break

    def _click_loop(self, global_interval_ms: int, actions: list[dict], mode: str, pure_background: bool) -> None:
        while not self._stop_event.is_set():
            for action in actions:
                if self._stop_event.is_set():
                    break
                
                normalize_mouse_action(action)
                action_type = action.get("type", "click")
                if is_position_action(action):
                    if mode == "window":
                        if not perform_window_mouse_action(action["hwnd"], action, pure_background):
                            pass # Or continue
                    else:
                        perform_screen_mouse_action(action)

                    # Determine wait time: per-step delay or global interval
                    delay_ms = action.get("delay")
                    if delay_ms is None:
                        delay_ms = global_interval_ms
                    
                    if delay_ms > 0 and self._stop_event.wait(delay_ms / 1000.0):
                        break
                elif action_type == "wait":
                    wait_ms = action.get("ms", 0)
                    if wait_ms > 0 and self._stop_event.wait(wait_ms / 1000.0):
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

    def export_script(self):
        """Save the current configuration to a JSON file."""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Export Script"
        )
        if file_path:
            try:
                write_script_file(file_path, self.collect_script_data())
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
            data = read_script_file(file_path)
        except Exception as e:
            messagebox.showerror("Import Error", f"Failed to read script: {e}")
            return
        self.apply_script_data(data, source_path=file_path)

    def on_close(self) -> None:
        self._stop_event.set()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    raise SystemExit(main())
