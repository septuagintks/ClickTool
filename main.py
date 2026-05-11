import ctypes
import threading
import tkinter as tk
from tkinter import ttk, messagebox

user32 = ctypes.windll.user32

INPUT_MOUSE = 0
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class INPUTUNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("type", ctypes.c_ulong), ("u", INPUTUNION)]


class ClickerApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Mouse Click Tool")
        self.root.resizable(False, False)

        self.interval_var = tk.StringVar(value="100")
        self.status_var = tk.StringVar(value="Ready")
        self._stop_event = threading.Event()
        self._click_thread: threading.Thread | None = None

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_ui(self) -> None:
        frame = ttk.Frame(self.root, padding=16)
        frame.grid(sticky="nsew")

        ttk.Label(frame, text="Interval (ms)").grid(row=0, column=0, sticky="w")
        interval_entry = ttk.Entry(frame, textvariable=self.interval_var, width=12)
        interval_entry.grid(row=0, column=1, padx=(8, 0), sticky="w")
        interval_entry.focus_set()

        button_row = ttk.Frame(frame)
        button_row.grid(row=1, column=0, columnspan=2, pady=(12, 0), sticky="ew")

        self.start_button = ttk.Button(button_row, text="Start", command=self.start_clicking)
        self.start_button.grid(row=0, column=0, padx=(0, 8))

        self.stop_button = ttk.Button(button_row, text="Stop", command=self.stop_clicking, state="disabled")
        self.stop_button.grid(row=0, column=1)

        ttk.Label(frame, textvariable=self.status_var).grid(row=2, column=0, columnspan=2, pady=(12, 0), sticky="w")

        ttk.Label(
            frame,
            text="Moves the cursor nowhere — it clicks at the current pointer position.",
            foreground="#666666",
        ).grid(row=3, column=0, columnspan=2, pady=(8, 0), sticky="w")

    def start_clicking(self) -> None:
        if self._click_thread and self._click_thread.is_alive():
            return

        try:
            interval = int(self.interval_var.get())
            if interval <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid interval", "Enter a positive whole number of milliseconds.")
            return

        self._stop_event.clear()
        self._click_thread = threading.Thread(target=self._click_loop, args=(interval,), daemon=True)
        self._click_thread.start()
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.status_var.set(f"Running every {interval} ms")

    def stop_clicking(self) -> None:
        self._stop_event.set()
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        self.status_var.set("Stopped")

    def _click_loop(self, interval_ms: int) -> None:
        interval_s = interval_ms / 1000.0
        while not self._stop_event.is_set():
            self._left_click()
            if self._stop_event.wait(interval_s):
                break
        self.root.after(0, self._reset_buttons)

    def _reset_buttons(self) -> None:
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        if not self._stop_event.is_set():
            self.status_var.set("Ready")

    def _left_click(self) -> None:
        extra = ctypes.c_ulong(0)
        input_size = ctypes.sizeof(INPUT)
        inputs = (INPUT * 2)()

        for index, flags in enumerate((MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP)):
            inputs[index].type = INPUT_MOUSE
            inputs[index].mi = MOUSEINPUT(0, 0, 0, flags, 0, ctypes.pointer(extra))

        user32.SendInput(2, ctypes.byref(inputs), input_size)

    def on_close(self) -> None:
        self._stop_event.set()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    ClickerApp().run()
