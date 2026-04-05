from __future__ import annotations

import os
import pathlib
import uuid
from typing import Iterable, Tuple


RenameOp = Tuple[str, str]  # (old_path, new_path)


def two_phase_rename(mods_dir: str, ops: Iterable[RenameOp]) -> None:
    """Apply a batch of folder renames under `mods_dir` using a two-phase scheme.

    This avoids collisions when swapping names (A->B, B->A) by renaming everything
    to temporary unique names first, then to the final names.

    Raises:
        RuntimeError: if any target exists or if a rename fails.
    """

    ops_list = [(str(a), str(b)) for a, b in (ops or []) if a and b]
    if not ops_list:
        return

    mods_dir = str(mods_dir)
    token = uuid.uuid4().hex[:8]

    # IMPORTANT: Some mods are discovered as nested directories (e.g. Mods/Wrapper/RealMod).
    # If we rename the wrapper first, the nested old_path no longer exists and the batch fails.
    # Sort by path depth so children are moved out before parents.
    def _depth(p: str) -> int:
        try:
            return len(pathlib.Path(p).parts)
        except Exception:
            return len(str(p).split(os.sep))

    ops_sorted = sorted(ops_list, key=lambda t: _depth(t[0]), reverse=True)

    tmp_ops = []  # (old, tmp, final)
    for i, (old_path, new_path) in enumerate(ops_sorted):
        tmp_name = f"__TMP_RENAME__{token}_{i:04d}"
        tmp_path = str(pathlib.Path(mods_dir) / tmp_name)
        tmp_ops.append((old_path, tmp_path, new_path))

    # Phase 1: old -> tmp
    for old_path, tmp_path, _final in tmp_ops:
        os.rename(old_path, tmp_path)

    # Phase 2: tmp -> final
    for _old_path, tmp_path, final_path in tmp_ops:
        if os.path.exists(final_path):
            raise RuntimeError(f"Target already exists: {pathlib.Path(final_path).name}")
        os.rename(tmp_path, final_path)
