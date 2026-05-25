import argparse
import os
import sys
import time
import tkinter as tk

from clicktool_min.winapi import user32, kernel32, sleep_until_deadline, enable_dpi_awareness
from clicktool_min.paths import (
    get_auto_config_path, get_auto_log_path, write_auto_log,
    acquire_single_instance_mutex, release_single_instance_mutex,
    show_already_running_message,
)
from clicktool_min.script import (
    coerce_non_negative_int, coerce_wheel_delta, infer_script_mode,
    is_position_action, normalize_mouse_action, read_script_file,
    DEFAULT_AUTO_LOOP_TIMEOUT_SECONDS, DEFAULT_AUTO_LOOP_MAX_ROUNDS,
    DEFAULT_TARGET_WAIT_SECONDS,
)
from clicktool_min.window import (
    wait_for_windows, resolve_hwnd_by_title,
    perform_screen_mouse_action, perform_window_mouse_action,
    perform_screen_key_action, perform_window_key_action,
)
from clicktool_min.ui import ClickerApp


def run_auto_config(config_path: str, log_path: str | None = None) -> int:
    write_auto_log(log_path, f"auto run started; config={config_path}")
    if not os.path.exists(config_path):
        write_auto_log(log_path, "auto config not found; exit=2")
        return 2
    try:
        data = read_script_file(config_path)
    except Exception:
        # read_script_file already logged the full stack trace via log_error()
        # Just log the exit code here to avoid duplicate stack traces
        write_auto_log(log_path, "failed to read config (see error above); exit=2")
        return 2

    mode = infer_script_mode(data)
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

    window_map = {}
    if mode == "window":
        titles = set(data.get("target_windows", []))
        titles.update(p.get("win_title") for p in fallback_actions if isinstance(p, dict) and p.get("win_title"))
        window_map = wait_for_windows(sorted(titles), target_wait_seconds, log_path)

    actions = []
    for p in raw_actions:
        if not isinstance(p, dict):
            write_auto_log(log_path, f"skipped non-dict action: {type(p).__name__}")
            continue
        normalize_mouse_action(p)
        ptype = p.get("type", "click")
        if ptype == "wait":
            actions.append({"type": "wait", "ms": coerce_non_negative_int(p.get("ms"), 0)})
        elif is_position_action(p) or ptype == "key":
            entry = dict(p)
            if mode == "window":
                hwnd = window_map.get(p.get("win_title"))
                if not hwnd:
                    write_auto_log(log_path, f"missing window position title={p.get('win_title')}")
                    continue
                entry["hwnd"] = hwnd
            actions.append(entry)
        else:
            write_auto_log(log_path, f"unknown action type={ptype}; skipped")

    runnable_count = sum(1 for a in actions if a.get("type") != "wait")
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
                    title = action.get("win_title")
                    found_hwnd = resolve_hwnd_by_title(title)
                    if found_hwnd:
                        hwnd = found_hwnd
                        action["hwnd"] = hwnd
                        write_auto_log(log_path, f"re-resolved window '{title}' to HWND {hwnd}")
                if hwnd and user32.IsWindow(hwnd):
                    if is_position_action(action):
                        if perform_window_mouse_action(hwnd, action):
                            clicks += 1
                            write_auto_log(log_path, f"ran window action type={ptype} title={action.get('win_title')} x={action.get('x')} y={action.get('y')}")
                        else:
                            write_auto_log(log_path, f"skipped window action outside client area type={ptype} title={action.get('win_title')} x={action.get('x')} y={action.get('y')}")
                    elif ptype == "key":
                        if perform_window_key_action(hwnd, action):
                            clicks += 1
                            write_auto_log(log_path, f"ran window key action title={action.get('win_title')} key={action.get('key_name')}")
                        else:
                            write_auto_log(log_path, f"failed window key action title={action.get('win_title')} key={action.get('key_name')}")
                else:
                    write_auto_log(log_path, f"missing window for action title={action.get('win_title')}")
            else:
                if is_position_action(action):
                    if perform_screen_mouse_action(action):
                        clicks += 1
                        write_auto_log(log_path, f"ran screen action type={ptype} x={action.get('x')} y={action.get('y')}")
                    else:
                        write_auto_log(log_path, f"failed screen action type={ptype} x={action.get('x')} y={action.get('y')}")
                elif ptype == "key":
                    if perform_screen_key_action(action):
                        clicks += 1
                        write_auto_log(log_path, f"ran screen key action key={action.get('key_name')}")
                    else:
                        write_auto_log(log_path, f"failed screen key action key={action.get('key_name')}")

            delay_ms = action.get("delay") if action.get("delay") is not None else global_interval_ms
            if delay_ms > 0:
                sleep_until_deadline(delay_ms / 1000.0, deadline)
        rounds += 1
        write_auto_log(log_path, f"finished round {rounds}; clicks={clicks}")
        if not loop_enabled or (max_rounds > 0 and rounds >= max_rounds):
            break
        sleep_until_deadline(0.001, deadline)

    write_auto_log(log_path, "auto run finished; exit=0")
    return 0


def parse_args(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description="ClickTool Minified - A zero-dependency auto clicker")
    parser.add_argument("--auto", action="store_true", help="Run in auto mode using the provided config")
    parser.add_argument("--config", type=str, help="Path to the JSON config file (default: auto_config.json in app data)")
    parser.add_argument("--silent", action="store_true", help="Suppress console window in auto mode")
    return parser.parse_args(argv)


def _reexec_with_pythonw_if_needed(is_auto_mode: bool, argv: list[str]):
    """If running with python.exe (has console) and NOT in auto mode, re-exec with pythonw.exe."""
    executable = sys.executable
    if not executable.lower().endswith("python.exe"):
        return

    if is_auto_mode:
        return

    pythonw = executable.lower().replace("python.exe", "pythonw.exe")
    if os.path.exists(pythonw):
        import subprocess
        # DETACHED_PROCESS = 0x00000008
        subprocess.Popen([pythonw] + argv, creationflags=0x00000008)
        sys.exit(0)
    else:
        # Fallback: hide console if pythonw.exe not found
        try:
            kernel32.FreeConsole()
        except (AttributeError, OSError):
            pass


def main(argv: list[str] | None = None):
    args = parse_args(argv)
    enable_dpi_awareness()

    if args.auto:
        if args.silent:
            kernel32.FreeConsole()

        config_path = args.config or get_auto_config_path()
        log_path = get_auto_log_path()

        mutex = acquire_single_instance_mutex()
        if not mutex:
            write_auto_log(log_path, "another instance is already running; exit=4")
            return 4

        try:
            return run_auto_config(config_path, log_path)
        finally:
            release_single_instance_mutex(mutex)
    else:
        _reexec_with_pythonw_if_needed(is_auto_mode=False, argv=argv if argv is not None else sys.argv)

        mutex = acquire_single_instance_mutex()
        if not mutex:
            show_already_running_message()
            return 4

        try:
            app = ClickerApp()
            app.root.mainloop()
        finally:
            release_single_instance_mutex(mutex)

    return 0


if __name__ == "__main__":
    sys.exit(main())
