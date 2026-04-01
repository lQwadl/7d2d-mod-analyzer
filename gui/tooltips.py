from __future__ import annotations

from typing import Any, Optional

import tkinter as tk


class HighRiskTooltip:
    def __init__(self, root: tk.Tk, table: Any, mod_lookup: dict, *, text: str):
        self.root = root
        self.table = table
        self.mod_lookup = mod_lookup
        self.text = text

        self._tooltip: Optional[tk.Toplevel] = None
        self._label: Optional[tk.Label] = None

    def install(self) -> None:
        def on_motion(event: Any) -> None:
            try:
                row = self.table.identify_row(event.y)
                if not row:
                    self.hide()
                    return
                mod = self.mod_lookup.get(row)
                if mod and getattr(mod, "high_risk", False):
                    self.show(event.x_root, event.y_root)
                else:
                    self.hide()
            except Exception:
                self.hide()

        self.table.bind("<Motion>", on_motion)

    def show(self, x: int, y: int) -> None:
        try:
            if self._tooltip is None:
                self._tooltip = tk.Toplevel(self.root)
                self._tooltip.wm_overrideredirect(True)
                lbl = tk.Label(
                    self._tooltip,
                    text=self.text,
                    bg="#000000",
                    fg="#FFD54F",
                    relief="solid",
                    borderwidth=1,
                    font=("Segoe UI", 9),
                )
                lbl.pack()
                self._label = lbl
            else:
                if self._label is not None:
                    self._label.config(text=self.text)
            self._tooltip.wm_geometry(f"+{x + 12}+{y + 12}")
            self._tooltip.deiconify()
        except Exception:
            pass

    def hide(self) -> None:
        try:
            if self._tooltip is not None:
                self._tooltip.withdraw()
        except Exception:
            pass
