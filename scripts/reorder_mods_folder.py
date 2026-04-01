"""Reorder and (optionally) rename a 7 Days to Die Mods folder.

- Reads the Mods folder, computes a deterministic load order (including
  explicit RWG/POI constraints), and produces a rename plan using numeric
  prefixes: 000_, 010_, 020_, ...
- Does NOT modify internal mod files.

Usage:
  python scripts/reorder_mods_folder.py --dry-run
  python scripts/reorder_mods_folder.py --apply
  python scripts/reorder_mods_folder.py --mods-path "D:/Steam/steamapps/common/7 Days To Die/Mods" --apply
"""

from __future__ import annotations

# Ensure repo root is on sys.path when running as a script.
import sys

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from logic.load_order_engine import compute_load_order
from logic.load_order import apply_load_order_to_mod_folders


@dataclass
class FolderMod:
    name: str
    path: str
    disabled: bool = False
    disabled_reason: Optional[str] = None
    is_patch: bool = False
    is_overhaul: bool = False
    categories: list = None
    category: str = "Miscellaneous"
    conflicts: list = None

    def __post_init__(self):
        if self.categories is None:
            self.categories = []
        if self.conflicts is None:
            self.conflicts = []


def _load_config_mods_path(repo_root: Path) -> Optional[str]:
    cfg_path = repo_root / "config.json"
    if not cfg_path.exists():
        return None
    try:
        data = json.loads(cfg_path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            raw = data.get("mods_path")
            if raw and str(raw).strip():
                return str(raw)
    except Exception:
        return None
    return None


def _iter_mod_folders(mods_path: Path) -> List[FolderMod]:
    mods: List[FolderMod] = []

    for child in mods_path.iterdir():
        if not child.is_dir():
            continue

        name = child.name

        # Skip our own temp collision-avoidance folders if present.
        if name.startswith("__TMP_RENAME__"):
            continue

        # Heuristic: treat __DISABLED__ folders as disabled.
        disabled = name.startswith("__DISABLED__")

        mods.append(FolderMod(name=name, path=str(child.resolve()), disabled=disabled))

    return mods


def _write_plan_file(out_path: Path, ops: List[Tuple[str, str]], warnings: List[str]) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines: List[str] = []

    if warnings:
        lines.append("=== WARNINGS ===\n")
        for w in warnings:
            lines.append(f"- {w}\n")
        lines.append("\n")

    lines.append("=== RENAME PLAN (OLD -> NEW) ===\n")
    for old_path, new_path in ops:
        lines.append(f"{Path(old_path).name}  ->  {Path(new_path).name}\n")

    out_path.write_text("".join(lines), encoding="utf-8")


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]

    ap = argparse.ArgumentParser()
    ap.add_argument("--mods-path", default=None, help="Path to the 7DTD Mods folder")
    ap.add_argument("--step", type=int, default=10, help="Numeric prefix step (default: 10 => 000, 010, 020, ...)")
    ap.add_argument("--apply", action="store_true", help="Apply renames")
    ap.add_argument("--dry-run", action="store_true", help="Only print/write the plan (default)")
    ap.add_argument(
        "--plan-out", default=str(repo_root / "data" / "mods_rename_plan.txt"), help="Output plan text file"
    )

    args = ap.parse_args()

    mods_path = args.mods_path or _load_config_mods_path(repo_root)
    if not mods_path:
        raise SystemExit("No mods path provided and config.json has no mods_path")

    mods_dir = Path(mods_path)
    if not mods_dir.exists() or not mods_dir.is_dir():
        raise SystemExit(f"Mods path does not exist or is not a folder: {mods_dir}")

    mods = _iter_mod_folders(mods_dir)
    enabled = [m for m in mods if not m.disabled]

    ordered, report = compute_load_order(enabled, include_disabled=False)

    # Build plan using the shared rename function, but in dry-run mode.
    ops = apply_load_order_to_mod_folders(ordered, str(mods_dir), step=args.step, dry_run=True)

    warnings = list(getattr(report, "warnings", []) or [])
    errors = list(getattr(report, "errors", []) or [])
    if errors:
        # Don’t apply if engine found blockers; still write plan.
        warnings = ["BLOCKING: " + e for e in errors] + warnings

    plan_out = Path(args.plan_out)
    _write_plan_file(plan_out, ops, warnings)

    print(f"Mods folder: {mods_dir}")
    print(f"Planned renames: {len(ops)}")
    print(f"Plan written: {plan_out}")

    # Print the new naming structure in order
    print("\n=== NEW FOLDER ORDER ===")
    for _old, new in ops:
        print(Path(new).name)

    if args.apply and not errors:
        apply_load_order_to_mod_folders(ordered, str(mods_dir), step=args.step, dry_run=False)
        print("\nApplied folder renames successfully.")
        return 0

    if args.apply and errors:
        print("\nNot applying due to blocking errors; see plan file for details.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
