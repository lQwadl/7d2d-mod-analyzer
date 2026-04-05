from __future__ import annotations

from typing import Any

import tkinter as tk
from tkinter import ttk

from logic.category_policy import CATEGORY_ORDER, normalize_category


TAG_COLORS = {
    "ok": "#3fb950",
}


def build_heatmap_panel(app: Any, root: tk.Widget) -> None:
    panel = tk.Frame(root, bg=app.colors.get("panel", "#252526"))
    panel.pack(fill="x", padx=10, pady=(4, 8))
    header = tk.Frame(panel, bg=app.colors.get("panel", "#252526"))
    header.pack(fill="x")
    tk.Label(
        header,
        text="Risk Heatmap",
        fg="#ffffff",
        bg=app.colors.get("panel", "#252526"),
        font=("Segoe UI", 9, "bold"),
    ).pack(side="left", anchor="w")

    try:
        tk.Button(
            header,
            text="All Categories",
            command=lambda: heatmap_reset(app),
            bg=app.colors.get("button_bg", "#2d2d2d"),
            fg=app.colors.get("button_fg", "#d4d4d4"),
            relief="flat",
            padx=10,
            pady=2,
        ).pack(side="right")
    except Exception:
        pass

    heat_wrap = tk.Frame(panel, bg=app.colors.get("panel", "#252526"))
    heat_wrap.pack(fill="x")
    app.heatmap_canvas = tk.Canvas(
        heat_wrap,
        height=160,
        bg=app.colors.get("panel", "#252526"),
        highlightthickness=0,
    )
    vsb = ttk.Scrollbar(heat_wrap, orient="vertical", command=app.heatmap_canvas.yview)
    app.heatmap_canvas.configure(yscrollcommand=vsb.set)
    app.heatmap_canvas.pack(side="left", fill="x", expand=True)
    vsb.pack(side="right", fill="y")

    def _on_wheel(event: Any) -> None:
        try:
            app.heatmap_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except Exception:
            pass

    app.heatmap_canvas.bind("<MouseWheel>", _on_wheel)

    update_heatmap(app)


def update_heatmap(app: Any) -> None:
    try:
        if not hasattr(app, "heatmap_canvas") or app.heatmap_canvas is None:
            return
        c = app.heatmap_canvas
        c.delete("all")

        stats: dict[str, dict[str, int]] = {}
        for m in getattr(app, "mods", None) or []:
            mod_cats = getattr(m, "categories", None) or [normalize_category(getattr(m, "category", None))]
            for cat in mod_cats:
                st = stats.setdefault(cat, {"total": 0, "high": 0})
                st["total"] += 1
                if getattr(m, "severity", 0) >= 60:
                    st["high"] += 1

        x_pad, y_pad = 10, 6
        width = c.winfo_width() or 600
        max_bar = width - 220
        y = y_pad

        selected = getattr(app, "heatmap_selected_category", None)

        # First row: All Categories (reset)
        try:
            tag = "hm::ALL"
            label = "All Categories" if not selected else f"All Categories (selected: {selected})"
            c.create_text(
                x_pad,
                y + 10,
                text=label,
                anchor="w",
                fill=app.colors.get("tree_fg", "#d4d4d4"),
                font=("Segoe UI", 9, "bold"),
                tags=(tag,),
            )
            c.create_rectangle(200, y, 200 + max_bar, y + 20, fill="#1f1f1f", width=0, tags=(tag,))
            c.create_text(
                200 + max_bar + 6,
                y + 10,
                text="",
                anchor="w",
                fill=app.colors.get("tree_fg", "#d4d4d4"),
                font=("Segoe UI", 9),
                tags=(tag,),
            )
            c.tag_bind(tag, "<Button-1>", lambda e: heatmap_reset(app))
            c.tag_bind(tag, "<Enter>", lambda e: c.configure(cursor="hand2"))
            c.tag_bind(tag, "<Leave>", lambda e: c.configure(cursor="arrow"))
            y += 24
        except Exception:
            pass

        for cat in CATEGORY_ORDER or []:
            st = stats.get(cat)
            if not st:
                continue
            total = st["total"]
            risk = (st["high"] / total) if total else 0.0

            if risk < 0.2:
                color = TAG_COLORS.get("ok", "#3fb950")
            elif risk < 0.5:
                color = "#E6B800"
            else:
                color = "#FF8C00"

            bar_len = int(max_bar * risk)
            tag = f"hm::{cat}"
            is_selected = selected == cat

            c.create_text(
                x_pad,
                y + 10,
                text=cat,
                anchor="w",
                fill="#FFD54F" if is_selected else app.colors.get("tree_fg", "#d4d4d4"),
                font=("Segoe UI", 9, "bold" if is_selected else "normal"),
                tags=(tag,),
            )
            c.create_rectangle(200, y, 200 + max_bar, y + 20, fill="#1f1f1f", width=0, tags=(tag,))
            c.create_rectangle(200, y, 200 + bar_len, y + 20, fill=color, width=0, tags=(tag,))

            if is_selected:
                c.create_rectangle(
                    200,
                    y,
                    200 + max_bar,
                    y + 20,
                    outline="#FFD54F",
                    width=2,
                    tags=(tag,),
                )

            c.create_text(
                200 + max_bar + 6,
                y + 10,
                text=f"{int(risk * 100)}%",
                anchor="w",
                fill=app.colors.get("tree_fg", "#d4d4d4"),
                font=("Segoe UI", 9),
                tags=(tag,),
            )

            try:
                c.tag_bind(tag, "<Button-1>", lambda e, _cat=cat: heatmap_select_category(app, _cat))
                c.tag_bind(tag, "<Enter>", lambda e: c.configure(cursor="hand2"))
                c.tag_bind(tag, "<Leave>", lambda e: c.configure(cursor="arrow"))
            except Exception:
                pass
            y += 24

        try:
            c.configure(scrollregion=c.bbox("all"))
        except Exception:
            pass
    except Exception:
        pass


def heatmap_select_category(app: Any, category_name: str) -> None:
    try:
        cat = normalize_category(category_name)
        if getattr(app, "heatmap_selected_category", None) == cat:
            return heatmap_reset(app)
        app.heatmap_selected_category = cat
        app._set_category_filter(cat)
        app.refresh_table()
        update_heatmap(app)
        try:
            app.jump_to_category(cat)
        except Exception:
            pass
    except Exception:
        pass


def heatmap_reset(app: Any) -> None:
    try:
        app.heatmap_selected_category = None
        app._set_category_filter("All")
        app.refresh_table()
        update_heatmap(app)
    except Exception:
        pass
