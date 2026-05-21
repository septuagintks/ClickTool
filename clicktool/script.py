import json
import os

from .hotkey import DEFAULT_HOTKEYS, normalize_hotkey_text

DOT_SIZE = 40
DEFAULT_AUTO_LOOP_TIMEOUT_SECONDS = 60
DEFAULT_AUTO_LOOP_MAX_ROUNDS = 3
DEFAULT_TARGET_WAIT_SECONDS = 60
DEFAULT_PURE_BACKGROUND_WINDOW_CLICK = True
DEFAULT_INTERVAL_MS = 500
DEFAULT_WAIT_MS = 500

POSITION_ACTION_TYPES = {"click", "wheel"}
MOUSE_BUTTONS = ("left", "right", "middle", "x1", "x2")
MOUSE_BUTTON_LABELS = {
    "left": "Left",
    "right": "Right",
    "middle": "Middle",
    "x1": "Side 1",
    "x2": "Side 2",
}


def coerce_non_negative_int(value, default: int) -> int:
    try:
        value = int(value)
    except (TypeError, ValueError):
        return default
    return max(0, value)


def infer_script_mode(data: dict) -> str:
    return data.get("mode") or ("window" if data.get("window_positions") else "screen")


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
    data["mode"] = infer_script_mode(data)
    settings = data.setdefault("settings", {})
    settings.setdefault("window_client_area_only", DEFAULT_PURE_BACKGROUND_WINDOW_CLICK)
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
