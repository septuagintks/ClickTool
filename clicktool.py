import argparse
import os
import sys
import time

from clicktool.winapi import enable_dpi_awareness
from clicktool.paths import (
    get_auto_config_path, get_auto_log_path, write_auto_log,
    acquire_single_instance_mutex, release_single_instance_mutex,
    show_already_running_message,
)
from clicktool.script import (
    coerce_non_negative_int, coerce_wheel_delta, is_position_action,
    normalize_mouse_action, read_script_file,
    DEFAULT_AUTO_LOOP_TIMEOUT_SECONDS, DEFAULT_AUTO_LOOP_MAX_ROUNDS,
    DEFAULT_TARGET_WAIT_SECONDS,
)
from clicktool.window import (
    list_visible_windows, wait_for_windows,
    perform_screen_mouse_action, perform_window_mouse_action,
)
from clicktool.ui import ClickerApp
import win32gui


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
                if not hwnd or not win32gui.IsWindow(hwnd):
                    active_windows = list_visible_windows()
                    title = action.get("win_title")
                    found_hwnd = next((h for h, t in active_windows if t == title), None)
                    if not found_hwnd and title:
                        found_hwnd = next((h for h, t in active_windows if title.lower() in t.lower()), None)
                    if found_hwnd:
                        hwnd = found_hwnd
                        action["hwnd"] = hwnd
                        write_auto_log(log_path, f"re-resolved window '{title}' to HWND {hwnd}")
                if hwnd and win32gui.IsWindow(hwnd):
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
    parser = argparse.ArgumentParser(description="Mouse Click Tool")
    parser.add_argument("--auto", action="store_true", help="Run saved auto startup config")
    parser.add_argument("--silent", action="store_true", help="Suppress UI messages in automation mode")
    parser.add_argument("--config", help="Optional config path for --auto")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

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

        enable_dpi_awareness()
        ClickerApp().run()
        return 0
    finally:
        release_single_instance_mutex(mutex_handle)


if __name__ == "__main__":
    raise SystemExit(main())
