import argparse
import os
import sys
import time

from clicktool.winapi import user32, kernel32, sleep_until_deadline
from clicktool.paths import (
    get_auto_config_path, get_auto_log_path, write_auto_log,
    acquire_single_instance_mutex, release_single_instance_mutex,
    show_already_running_message,
)
from clicktool.script import (
    coerce_non_negative_int, coerce_bool, infer_script_mode,
    is_position_action, normalize_mouse_action, read_script_file,
    DEFAULT_AUTO_LOOP_TIMEOUT_SECONDS, DEFAULT_AUTO_LOOP_MAX_ROUNDS,
    DEFAULT_TARGET_WAIT_SECONDS,
)
from clicktool.window import (
    wait_for_windows, resolve_hwnd_by_title,
    perform_screen_mouse_action, perform_window_mouse_action,
    perform_screen_key_action, perform_window_key_action,
)
from clicktool.ui import ClickerApp


def is_runnable_auto_action(action: dict) -> bool:
    return is_position_action(action) or action.get("type") == "key"


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
    loop_enabled = coerce_bool(data.get("loop"), True)
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
        titles.update(p.get("win_title") for p in fallback_actions if isinstance(p, dict) and p.get("win_title"))
        titles.update(p.get("win_title") for p in raw_actions if isinstance(p, dict) and p.get("win_title"))
        titles.discard(None)
        titles = sorted(titles)
        window_map = wait_for_windows(titles, target_wait_seconds, log_path)
        actions = []
        for p in raw_actions:
            if not isinstance(p, dict):
                write_auto_log(log_path, f"invalid action (not a dict): {type(p).__name__}; skipped")
                continue
            normalize_mouse_action(p)
            ptype = p.get("type", "click")
            if ptype == "wait":
                actions.append({"type": "wait", "ms": coerce_non_negative_int(p.get("ms"), 0)})
                continue
            if not is_runnable_auto_action(p):
                write_auto_log(log_path, f"unknown action type={ptype}; skipped")
                continue
            entry = dict(p)
            hwnd = window_map.get(p.get("win_title"))
            if hwnd:
                entry["hwnd"] = hwnd
                actions.append(entry)
            else:
                write_auto_log(log_path, f"missing window position title={p.get('win_title')}")
    else:
        actions = []
        for p in raw_actions:
            if not isinstance(p, dict):
                write_auto_log(log_path, f"invalid action (not a dict): {type(p).__name__}; skipped")
                continue
            normalize_mouse_action(p)
            ptype = p.get("type", "click")
            if ptype == "wait":
                actions.append({"type": "wait", "ms": coerce_non_negative_int(p.get("ms"), 0)})
                continue
            if not is_runnable_auto_action(p):
                write_auto_log(log_path, f"unknown action type={ptype}; skipped")
                continue
            entry = dict(p)
            actions.append(entry)

    runnable_count = sum(1 for a in actions if is_runnable_auto_action(a))
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
                else:
                    write_auto_log(log_path, f"unknown action type={ptype}; skipped")

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
        # Yield 1ms each round so configs with all-zero delays don't pin a CPU core
        sleep_until_deadline(0.001, deadline)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Mouse Click Tool")
    parser.add_argument("--auto", action="store_true", help="Run saved auto startup config")
    parser.add_argument("--silent", action="store_true", help="Suppress UI messages in automation mode")
    parser.add_argument("--config", help="Optional config path for --auto")
    return parser.parse_args(argv)


def _reexec_with_pythonw_if_needed(args) -> bool:
    """Re-launch under pythonw.exe to drop the console window (GUI mode only).

    Returns True (and spawns pythonw child) so main() can exit immediately.
    Returns False when re-exec is not needed or not possible.
    """
    if args.auto:
        return False
    if getattr(sys, "frozen", False):
        return False
    exe = os.path.basename(sys.executable).lower()
    if exe != "python.exe":
        return False
    pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    if not os.path.exists(pythonw):
        try:
            kernel32.FreeConsole()
        except (AttributeError, OSError):
            pass
        return False
    import subprocess
    DETACHED_PROCESS = 0x00000008
    CREATE_NEW_PROCESS_GROUP = 0x00000200
    subprocess.Popen(
        [pythonw, *sys.argv],
        creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
        close_fds=True,
    )
    return True


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if _reexec_with_pythonw_if_needed(args):
        return 0

    if args.auto and args.silent:
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
