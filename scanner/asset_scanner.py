from __future__ import annotations

import os
from typing import Iterable, Set


def scan_asset_files(mod_root: str) -> Set[str]:
    """Return normalized relative paths for non-XML files in a mod.

    - Excludes ModInfo.xml
    - Excludes all .xml (Config patches and UI/XUi)
    - Normalizes to lowercase forward-slash paths

    This is used for 'asset_conflict' detection (visual/audio/model overrides).
    """

    out: Set[str] = set()
    root = str(mod_root or "")
    if not root or not os.path.isdir(root):
        return out

    for dirpath, _, filenames in os.walk(root):
        for fn in filenames or []:
            try:
                if not fn:
                    continue
                if fn.lower() == "modinfo.xml":
                    continue
                if fn.lower().endswith(".xml"):
                    continue

                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, root)
                rel = str(rel).replace("\\", "/").lower()

                # Skip obvious metadata files
                if rel.endswith("/.ds_store") or rel.endswith("thumbs.db"):
                    continue

                out.add(rel)
            except Exception:
                continue

    return out
