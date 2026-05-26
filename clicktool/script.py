import json
import os

from .hotkey import DEFAULT_HOTKEYS, normalize_hotkey_text
from .paths import get_auto_log_path, log_error

DOT_SIZE = 40
DEFAULT_AUTO_LOOP_TIMEOUT_SECONDS = 60
DEFAULT_AUTO_LOOP_MAX_ROUNDS = 3
DEFAULT_TARGET_WAIT_SECONDS = 60
DEFAULT_PURE_BACKGROUND_WINDOW_CLICK = True
DEFAULT_INTERVAL_MS = 500
DEFAULT_WAIT_MS = 500
DEFAULT_ENABLE_GLOBAL_HOTKEYS = True

POSITION_ACTION_TYPES = {"click", "wheel"}
MOUSE_BUTTONS = ("left", "right", "middle", "x1", "x2")
MOUSE_BUTTON_LABELS = {
    "left": "Left",
    "right": "Right",
    "middle": "Middle",
    "x1": "Side 1",
    "x2": "Side 2",
}
KEY_MODIFIERS = ("Ctrl", "Alt", "Shift", "Win")


def coerce_bool(value, default: bool) -> bool:
    """Coerce JSON value to boolean, handling string 'false'/'true' correctly."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() not in ("false", "0", "")
    return bool(value) if value is not None else default


def coerce_non_negative_int(value, default: int) -> int:
    try:
        value = int(value)
    except (TypeError, ValueError):
        return default
    return max(0, value)


def coerce_optional_non_negative_int(value):
    if value is None:
        return None
    try:
        value = int(value)
    except (TypeError, ValueError):
        return None
    return value if value >= 0 else None


def coerce_int_or(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        try:
            return int(round(float(value)))
        except (TypeError, ValueError):
            return default


def infer_script_mode(data: dict) -> str:
    if data.get("mode"):
        return data["mode"]
    if data.get("window_positions"):
        return "window"
    if data.get("target_windows"):
        return "window"
    return "screen"


def is_position_action(action: dict) -> bool:
    return action.get("type", "click") in POSITION_ACTION_TYPES


def normalize_mouse_action(action: dict) -> dict:
    action_type = action.get("type", "click")
    if action_type == "click":
        button = str(action.get("button", "left")).lower()
        action["button"] = button if button in MOUSE_BUTTONS else "left"
        action["x"] = coerce_int_or(action.get("x"), 0)
        action["y"] = coerce_int_or(action.get("y"), 0)
        action["delay"] = coerce_optional_non_negative_int(action.get("delay"))
    elif action_type == "wheel":
        action["delta"] = coerce_wheel_delta(action.get("delta"), -1)
        action["x"] = coerce_int_or(action.get("x"), 0)
        action["y"] = coerce_int_or(action.get("y"), 0)
        action["delay"] = coerce_optional_non_negative_int(action.get("delay"))
    elif action_type == "wait":
        action["ms"] = coerce_non_negative_int(action.get("ms"), 0)
    elif action_type == "key":
        action["vk"] = coerce_int_or(action.get("vk"), 0)
        action["scan_code"] = coerce_int_or(action.get("scan_code"), 0)
        action["extended"] = coerce_bool(action.get("extended"), False)
        action["key_name"] = str(action.get("key_name") or "")
        raw_mods = action.get("modifiers") or []
        if isinstance(raw_mods, str):
            raw_mods = [raw_mods]
        seen: set[str] = set()
        normalized_mods: list[str] = []
        for m in raw_mods:
            name = str(m).strip().capitalize()
            if name in KEY_MODIFIERS and name not in seen:
                seen.add(name)
                normalized_mods.append(name)
        action["modifiers"] = [name for name in KEY_MODIFIERS if name in seen]
        action["mod_scans"] = action.get("mod_scans") or {}
        if not isinstance(action["mod_scans"], dict):
            action["mod_scans"] = {}
        action["delay"] = coerce_optional_non_negative_int(action.get("delay"))
    return action


def coerce_wheel_delta(value, default: int) -> int:
    try:
        value = int(value)
    except (TypeError, ValueError):
        return default
    return value if value != 0 else default


def format_key_combo(action: dict) -> str:
    modifiers = action.get("modifiers") or []
    key_name = action.get("key_name") or ""
    ordered = [name for name in KEY_MODIFIERS if name in modifiers]
    parts = [*ordered, key_name] if key_name else list(ordered)
    return "+".join(parts)


def get_mouse_action_name(action: dict) -> str:
    action_type = action.get("type", "click")
    if action_type == "click":
        button = action.get("button", "left")
        return f"Click {MOUSE_BUTTON_LABELS.get(button, 'Left')}"
    if action_type == "wheel":
        delta = coerce_wheel_delta(action.get("delta"), -1)
        direction = "Up" if delta > 0 else "Down"
        return f"Wheel {direction}"
    if action_type == "key":
        return "Key"
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
    if action_type == "key":
        combo = format_key_combo(action) or "(press a key)"
        return f"{prefix}{combo}{suffix}"
    return f"Delay: {action['ms']}ms"


def normalize_script_data(data: dict) -> dict:
    if not isinstance(data, dict):
        raise ValueError("Script data must be a dictionary")

    data["mode"] = infer_script_mode(data)
    if data["mode"] not in ("screen", "window"):
        data["mode"] = "screen"

    settings = data.setdefault("settings", {})
    if not isinstance(settings, dict):
        settings = data["settings"] = {}

    if "pure_background_window_click" not in settings and "window_client_area_only" in settings:
        settings["pure_background_window_click"] = coerce_bool(settings["window_client_area_only"], DEFAULT_PURE_BACKGROUND_WINDOW_CLICK)
    settings.pop("window_client_area_only", None)
    settings.setdefault("pure_background_window_click", DEFAULT_PURE_BACKGROUND_WINDOW_CLICK)
    settings["enable_global_hotkeys"] = coerce_bool(settings.get("enable_global_hotkeys"), DEFAULT_ENABLE_GLOBAL_HOTKEYS)
    settings["default_wait_ms"] = coerce_non_negative_int(
        settings.get("default_wait_ms"), DEFAULT_WAIT_MS
    )

    auto = data.setdefault("auto", {})
    if not isinstance(auto, dict):
        auto = data["auto"] = {}

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
    if not isinstance(hotkeys, dict):
        hotkeys = settings["hotkeys"] = {}

    for action, default in DEFAULT_HOTKEYS.items():
        hotkeys[action] = normalize_hotkey_text(hotkeys.get(action, default))

    for collection_name in ("screen_positions", "window_positions", "actions"):
        coll = data.setdefault(collection_name, [])
        if not isinstance(coll, list):
            data[collection_name] = []
        else:
            for action in coll:
                if isinstance(action, dict):
                    normalize_mouse_action(action)

    # Ensure target_windows is a list of strings
    tw = data.get("target_windows")
    if tw is None:
        data["target_windows"] = []
    elif not isinstance(tw, list):
        data["target_windows"] = []
    else:
        data["target_windows"] = [str(s) for s in tw if s is not None]

    return data


def read_script_file(file_path: str) -> dict:
    try:
        with open(file_path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        normalize_script_data(data)
        return data
    except Exception:
        log_error(get_auto_log_path(), f"read_script_file({file_path})")
        raise


def write_script_file(file_path: str, data: dict) -> None:
    directory = os.path.dirname(file_path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    temp_path = file_path + ".tmp"
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        os.replace(temp_path, file_path)
    except Exception:
        log_error(get_auto_log_path(), f"write_script_file({file_path})")
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        raise
