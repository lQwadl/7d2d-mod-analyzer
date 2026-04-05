from __future__ import annotations

import tkinter as tk


def build_visual_legend(root: tk.Misc) -> None:
    LEGEND_BORDER = "#3c3c3c"
    LEGEND_BG = "#1f1f1f"
    LEGEND_TEXT = "#cfcfcf"

    legend_outer = tk.Frame(root, bg=LEGEND_BORDER)
    legend_outer.pack(side="bottom", fill="x")

    legend = tk.Frame(legend_outer, bg=LEGEND_BG, padx=12, pady=8)
    legend.pack(fill="x", padx=1, pady=1)

    title = tk.Label(
        legend,
        text="Legend",
        fg="#ffffff",
        bg=LEGEND_BG,
        font=("Segoe UI", 9, "bold"),
    )
    title.pack(side="left", padx=(0, 16))

    def legend_item(parent: tk.Misc, color: str, title_txt: str, desc: str) -> None:
        row = tk.Frame(parent, bg=LEGEND_BG)
        row.pack(side="left", padx=12)

        swatch = tk.Canvas(row, width=14, height=14, bg=color, highlightthickness=0)
        swatch.pack(side="left", padx=(0, 6))

        lbl = tk.Label(row, text=f"{title_txt}: {desc}", fg=LEGEND_TEXT, bg=LEGEND_BG)
        lbl.pack(side="left")

    legend_item(legend, "#C62828", "Critical", "Save-breaking / missing dependency / invalid")
    legend_item(legend, "#FF8C00", "High", "Load order, XML override, dependency")
    legend_item(legend, "#FFD400", "Low", "Informational / cosmetic")
    legend_item(legend, "#1E88E5", "Redundant", "Covered by another mod")
    legend_item(legend, "#555555", "Disabled", "User disabled")
    legend_item(legend, "#4CAF50", "OK", "No issues")
