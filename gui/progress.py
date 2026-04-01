from __future__ import annotations

import tkinter as tk


class ProgressDialog:
    """Simple always-visible progress bar with centered percent text.

    Uses a Canvas so the percent text is always visible inside the bar.
    """

    def __init__(self, parent: tk.Misc, *, title: str = "Working…", width: int = 420, height: int = 22):
        self._parent = parent
        self._width = int(width)
        self._height = int(height)

        win = tk.Toplevel(parent)
        win.title(title)
        win.resizable(False, False)
        win.transient(parent)

        # Try to keep it on top during long operations
        try:
            win.attributes("-topmost", True)
        except Exception:
            pass

        self._win = win

        self._label_var = tk.StringVar(value=title)
        lbl = tk.Label(win, textvariable=self._label_var, anchor="w")
        lbl.pack(fill="x", padx=10, pady=(10, 6))

        canvas = tk.Canvas(win, width=self._width, height=self._height, highlightthickness=1)
        canvas.pack(padx=10, pady=(0, 10))
        self._canvas = canvas

        self._bg = "#2d2d2d"
        self._fill = "#0e639c"
        self._text = "#ffffff"

        self._bar_bg = canvas.create_rectangle(0, 0, self._width, self._height, fill=self._bg, outline="")
        self._bar_fill = canvas.create_rectangle(0, 0, 0, self._height, fill=self._fill, outline="")
        self._bar_text = canvas.create_text(
            self._width // 2,
            self._height // 2,
            text="0%",
            fill=self._text,
        )

        try:
            win.grab_set()
        except Exception:
            pass

        self.set_percent(0)

    def set_text(self, text: str) -> None:
        try:
            self._label_var.set(text)
        except Exception:
            pass
        self._flush()

    def set_percent(self, percent: int) -> None:
        try:
            pct = int(percent)
        except Exception:
            pct = 0
        if pct < 0:
            pct = 0
        if pct > 100:
            pct = 100

        fill_w = int(self._width * (pct / 100.0))
        try:
            self._canvas.coords(self._bar_fill, 0, 0, fill_w, self._height)
            self._canvas.itemconfigure(self._bar_text, text=f"{pct}%")
        except Exception:
            pass
        self._flush()

    def close(self) -> None:
        try:
            self._win.grab_release()
        except Exception:
            pass
        try:
            self._win.destroy()
        except Exception:
            pass

    def _flush(self) -> None:
        try:
            self._win.update_idletasks()
            self._win.update()
        except Exception:
            pass
