from .winapi import (
    user32, kernel32, POINT, RECT, INPUT, MOUSEINPUT, INPUT_MOUSE,
    MOUSEEVENTF_MOVE, MOUSEEVENTF_ABSOLUTE, MOUSEEVENTF_VIRTUALDESK, MOUSEEVENTF_WHEEL,
    SM_CXSCREEN, SM_CYSCREEN,
    SM_XVIRTUALSCREEN, SM_YVIRTUALSCREEN, SM_CXVIRTUALSCREEN, SM_CYVIRTUALSCREEN,
    WHEEL_DELTA,
    WM_MOUSEWHEEL,
    BUTTON_INPUT_MAP, BUTTON_MESSAGE_MAP,
    CWP_SKIPINVISIBLE, EnumWindowsProc,
    makelong, make_wparam, enable_dpi_awareness,
)
from .script import coerce_wheel_delta, normalize_mouse_action
import ctypes
import time


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


def list_visible_windows() -> list[tuple[int, str]]:
    windows: list[tuple[int, str]] = []

    def enum_callback(hwnd, lparam):
        if user32.IsWindowVisible(hwnd):
            title = get_window_title(hwnd)
            if title:
                windows.append((hwnd, title))
        return True

    cb = EnumWindowsProc(enum_callback)
    user32.EnumWindows(cb, 0)
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

    vx = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
    vy = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
    vw = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
    vh = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
    if vw <= 0 or vh <= 0:
        # Fallback to primary monitor when virtual desktop metrics aren't reported.
        vx, vy = 0, 0
        vw = max(1, user32.GetSystemMetrics(SM_CXSCREEN))
        vh = max(1, user32.GetSystemMetrics(SM_CYSCREEN))
    nx = int((x - vx) * 65535 / max(1, vw - 1))
    ny = int((y - vy) * 65535 / max(1, vh - 1))
    move_flags = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK

    inp_move = INPUT()
    inp_move.type = INPUT_MOUSE
    inp_move.iu.mi = MOUSEINPUT(nx, ny, 0, move_flags, 0, None)

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
