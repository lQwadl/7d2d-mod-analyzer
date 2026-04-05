from __future__ import annotations

import os
import pathlib
import re
import uuid

from logic.load_order_engine import compute_load_order, is_patch_mod_name
from logic.rename_sanitizer import apply_prefix_width


def sort_mods(mods):
    """Compute deterministic load order using the rule-based engine.

    This does not use numeric scoring; ordering is derived from constraints.
    """
    try:
        dedupe_keep_latest(mods)
    except Exception:
        pass

    ordered, _report = compute_load_order(mods, include_disabled=True)
    return ordered


def dedupe_keep_latest(mods):
    """Disable older duplicates by filesystem mtime.

    Heuristic: derive a base name by stripping a trailing dash/space + version-like
    suffix (e.g. "MyMod-1.2.3" -> "MyMod"). If no suffix is detected the
    full name is used as the base.
    """

    base_re = re.compile(r"^(.*?)(?:[-_ ]v?\d[\w\.-]*)$")

    groups = {}
    for mod in mods:
        match = base_re.match(mod.name)
        base = match.group(1) if match else mod.name
        base = base.strip().lower()
        groups.setdefault(base, []).append(mod)

    for _, items in groups.items():
        if len(items) <= 1:
            continue

        mtimes = []
        for mod in items:
            try:
                mt = os.path.getmtime(mod.path)
            except Exception:
                mt = 0
            mtimes.append((mt, mod))

        mtimes.sort(reverse=True, key=lambda x: x[0])
        keeper = mtimes[0][1]
        for _, mod in mtimes[1:]:
            mod.disabled = True
            mod.disabled_reason = f"Older version of {keeper.name}"

    return mods


def apply_load_order_to_mod_folders(ordered_mods, mods_path, *, step: int = 1, dry_run: bool = False):
    """Rename mod folders so 7 Days To Die loads them alphabetically.

    - Normal mods: 000-899
    - Patch mods (e.g. 999_ConflictPatch_*): 900-999
    """

    if not os.path.isdir(mods_path):
        raise FileNotFoundError(f"Mods path does not exist: {mods_path}")

    enabled = [m for m in (ordered_mods or []) if not bool(getattr(m, "disabled", False))]
    normal = [
        m
        for m in enabled
        if not bool(getattr(m, "is_patch", False)) and not is_patch_mod_name(str(getattr(m, "name", "") or ""))
    ]
    patches = [
        m
        for m in enabled
        if bool(getattr(m, "is_patch", False)) or is_patch_mod_name(str(getattr(m, "name", "") or ""))
    ]

    ops = []  # (old, new)

    try:
        step_i = int(step)
    except Exception:
        step_i = 1
    if step_i <= 0:
        step_i = 1

    max_normal = (max(0, (len(normal) - 1)) * step_i) if normal else 0
    max_patch = (900 + (max(0, (len(patches) - 1)) * step_i)) if patches else 0
    max_prefix = max(max_normal, max_patch)
    width = max(3, len(str(int(max_prefix))))

    for index, mod in enumerate(normal):
        old_path = str(getattr(mod, "path", "") or "")
        if not old_path or not os.path.isdir(old_path):
            continue
        folder = os.path.basename(old_path)
        new_name = apply_prefix_width(index * step_i, folder, width=width)
        ops.append((old_path, str(pathlib.Path(mods_path) / new_name)))

    patch_pref = 900
    for mod in patches:
        old_path = str(getattr(mod, "path", "") or "")
        if not old_path or not os.path.isdir(old_path):
            continue
        folder = os.path.basename(old_path)
        new_name = apply_prefix_width(patch_pref, folder, width=width)
        ops.append((old_path, str(pathlib.Path(mods_path) / new_name)))
        patch_pref += step_i
        if patch_pref > 999:
            raise RuntimeError("Too many patch mods (exceeds 3-digit ordering).")

    if dry_run:
        return ops

    # Two-phase rename to avoid collisions
    token = uuid.uuid4().hex[:8]
    tmp_ops = []  # (old, tmp, final)
    for i, (old_path, new_path) in enumerate(ops):
        if os.path.abspath(old_path) == os.path.abspath(new_path):
            continue
        tmp_path = str(pathlib.Path(mods_path) / f"__TMP_RENAME__{token}_{i:04d}")
        tmp_ops.append((old_path, tmp_path, new_path))

    for old_path, tmp_path, _final in tmp_ops:
        os.rename(old_path, tmp_path)
    for _old_path, tmp_path, final_path in tmp_ops:
        if os.path.exists(final_path):
            raise FileExistsError(f"Target folder already exists: {os.path.basename(final_path)}")
        os.rename(tmp_path, final_path)

    for mod in enabled:
        try:
            mod.name = os.path.basename(str(getattr(mod, "path", "") or ""))
        except Exception:
            pass

    return ops
