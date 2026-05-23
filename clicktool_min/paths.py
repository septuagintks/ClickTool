import os
import sys
import msvcrt
import tkinter as tk
from datetime import datetime
from tkinter import messagebox

from .winapi import (
    kernel32,
    ERROR_ALREADY_EXISTS,
)


APP_NAME = "ClickTool"
AUTO_CONFIG_FILENAME = "auto_config.json"
AUTO_LOG_DIRNAME = "logs"


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

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_dir = os.path.dirname(log_path)
    lock_path = os.path.join(log_dir, ".auto-minified.log.lock")

    try:
        # Create lock file and acquire exclusive lock
        # This ensures all operations (rotation check, write) are atomic across processes
        os.makedirs(log_dir, exist_ok=True)
        with open(lock_path, "a", encoding="utf-8") as lock_file:
            try:
                # Lock the entire lock file (byte 0, length 1)
                # This creates a global mutex across all processes
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
                try:
                    # Now we have exclusive access - check rotation and write
                    if os.path.exists(log_path) and os.path.getsize(log_path) > 1024 * 1024:
                        old_path = log_path + ".old"
                        os.replace(log_path, old_path)

                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(f"[{timestamp}] {message}\n")
                        f.flush()
                finally:
                    # Unlock
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
            except (OSError, IOError) as lock_err:
                # Lock acquisition failed - this should be rare
                # Fall back to best-effort write without lock
                try:
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(f"[{timestamp}] {message} [WARN: written without lock]\n")
                except OSError:
                    pass
    except OSError as e:
        try:
            print(f"[ClickTool] log write failed for {log_path}: {e}", file=sys.stderr)
        except OSError:
            pass


def log_error(log_path: str | None, context: str) -> None:
    import traceback
    write_auto_log(log_path, f"ERROR in {context}:\n{traceback.format_exc()}")


def acquire_single_instance_mutex() -> int | None:
    mutex_name = f"Local\\{APP_NAME}SingleInstance"
    handle = kernel32.CreateMutexW(None, False, mutex_name)
    if not handle:
        write_auto_log(get_auto_log_path(), f"WARN: CreateMutexW failed for {mutex_name}")
        return None
    if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        write_auto_log(
            get_auto_log_path(),
            f"INFO: Another instance already holds mutex {mutex_name}; handle={handle}"
        )
        kernel32.CloseHandle(handle)
        return None
    write_auto_log(get_auto_log_path(), f"INFO: Acquired single-instance mutex {mutex_name}; handle={handle}")
    return handle


def release_single_instance_mutex(handle: int | None) -> None:
    if handle:
        kernel32.CloseHandle(handle)


def show_already_running_message() -> None:
    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo("Already Running", "Click Tool is already running.")
    root.destroy()
