import ctypes
import time
import win32gui
import win32api

from .winapi import (
    user32, POINT, RECT, WM_MOUSEWHEEL, WHEEL_DELTA,
    MOUSEEVENTF_WHEEL, BUTTON_MESSAGE_MAP, BUTTON_INPUT_MAP,
    makelong, make_wparam,
)
from .script import coerce_wheel_delta, normalize_mouse_action


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


def list_visible_windows() -> list[tuple[int, str]]:
    windows: list[tuple[int, str]] = []

    def enum_callback(hwnd, lparam):
        if user32.IsWindowVisible(hwnd):
            title = get_window_title(hwnd)
            if title:
                windows.append((hwnd, title))
        return True

    win32gui.EnumWindows(enum_callback, None)
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
    from .paths import write_auto_log
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
        lparam = makelong(client_x, client_y)
        win32gui.PostMessage(target_hwnd, down_msg, make_wparam(down_low_word, down_high_word), lparam)
        win32gui.PostMessage(target_hwnd, up_msg, make_wparam(0, up_high_word), lparam)
        return True

    if action_type == "wheel":
        delta = coerce_wheel_delta(action.get("delta"), -1)
        win32gui.PostMessage(
            target_hwnd,
            WM_MOUSEWHEEL,
            make_wparam(0, delta * WHEEL_DELTA),
            makelong(screen_x, screen_y),
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
                if area < best_area:
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
