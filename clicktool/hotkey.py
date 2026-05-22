from .winapi import user32

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
    "add_key": "Ctrl+K",
    "clear": "Ctrl+Delete",
}

HOTKEY_ACTIONS = (
    ("start", "Start"),
    ("stop", "Stop"),
    ("add_window", "Add Window"),
    ("add_dot", "Add Dot"),
    ("add_wheel", "Add Wheel"),
    ("add_wait", "Add Wait"),
    ("add_key", "Add Key"),
    ("clear", "Clear"),
)

MODIFIER_STATE_BITS = {
    "Shift": 0x0001,
    "Ctrl": 0x0004,
    "Alt": 0x0008,
}
MODIFIER_KEYS = {
    "Shift_L", "Shift_R",
    "Control_L", "Control_R",
    "Alt_L", "Alt_R",
    "Meta_L", "Meta_R",
    "Super_L", "Super_R",
    "Win_L", "Win_R",
}
MODIFIER_VK_BY_NAME = {
    "Ctrl": (0x11,),
    "Alt": (0x12,),
    "Shift": (0x10,),
    "Win": (0x5B, 0x5C),
}
MODIFIER_ORDER = ("Ctrl", "Alt", "Shift", "Win")


def _is_modifier_pressed(name: str) -> bool:
    return any((user32.GetAsyncKeyState(vk) & 0x8000) != 0 for vk in MODIFIER_VK_BY_NAME[name])


def is_hotkey_pressed_globally(hotkey_str: str) -> bool:
    if not hotkey_str:
        return False
    parts = [p.strip().upper() for p in hotkey_str.split("+") if p.strip()]
    if not parts:
        return False
    needed = {name.upper() for name in MODIFIER_VK_BY_NAME}
    for name in MODIFIER_VK_BY_NAME:
        is_pressed = _is_modifier_pressed(name)
        if name.upper() in parts:
            if not is_pressed:
                return False
        else:
            if is_pressed:
                return False
    main_keys = [p for p in parts if p not in needed]
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
        "win": "Win",
        "super": "Win",
        "meta": "Win",
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
        if mapped in MODIFIER_VK_BY_NAME:
            if mapped not in modifiers:
                modifiers.append(mapped)
        else:
            key = mapped or canonical_key_name(part)

    if not key:
        return ""
    ordered_modifiers = [name for name in MODIFIER_ORDER if name in modifiers]
    return "+".join([*ordered_modifiers, key])


def hotkey_from_event(event) -> str:
    if event.keysym in MODIFIER_KEYS:
        return ""
    key = {
        "Escape": "Esc",
        "Return": "Enter",
        "space": "Space",
    }.get(event.keysym, canonical_key_name(event.keysym))
    modifiers: list[str] = [
        name
        for name in ("Ctrl", "Alt", "Shift")
        if event.state & MODIFIER_STATE_BITS[name]
    ]
    if _is_modifier_pressed("Win"):
        modifiers.append("Win")
    ordered = [name for name in MODIFIER_ORDER if name in modifiers]
    return "+".join([*ordered, key])


def modifier_name_from_keysym(keysym: str) -> str | None:
    if keysym in ("Control_L", "Control_R"):
        return "Ctrl"
    if keysym in ("Alt_L", "Alt_R"):
        return "Alt"
    if keysym in ("Shift_L", "Shift_R"):
        return "Shift"
    if keysym in ("Super_L", "Super_R", "Win_L", "Win_R", "Meta_L", "Meta_R"):
        return "Win"
    return None


def key_name_from_event(event) -> str:
    return {
        "Escape": "Esc",
        "Return": "Enter",
        "space": "Space",
    }.get(event.keysym, canonical_key_name(event.keysym))


def format_combo(modifiers: list[str], key_name: str) -> str:
    if not key_name:
        return ""
    ordered = [name for name in MODIFIER_ORDER if name in modifiers]
    return "+".join([*ordered, key_name])
