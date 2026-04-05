from __future__ import annotations

import os
from pathlib import Path
from typing import Type


def _norm(p: str | Path) -> Path:
    try:
        return Path(p).expanduser().resolve(strict=False)
    except Exception:
        return Path(str(p)).expanduser()


def _is_within(base: Path, child: Path) -> bool:
    try:
        b = _norm(base)
        c = _norm(child)
        return os.path.commonpath([str(b), str(c)]) == str(b)
    except Exception:
        return False


def is_appdata_path(path: str | Path) -> bool:
    """Return True if `path` is inside Windows AppData (Local/Roaming).

    We treat *any* AppData subtree as forbidden for mod scanning/deployment/sync.
    (AppData is reserved for UI state/saves/logs only.)
    """

    p = _norm(path)

    candidates: list[Path] = []

    # Environment variables are the most reliable.
    for env in ("LOCALAPPDATA", "APPDATA"):
        v = os.getenv(env)
        if v:
            candidates.append(_norm(v))

    # Fallbacks.
    try:
        home = Path.home()
        candidates.append(_norm(home / "AppData"))
        candidates.append(_norm(home / "AppData" / "Local"))
        candidates.append(_norm(home / "AppData" / "Roaming"))
    except Exception:
        pass

    # Quick heuristic for non-existent paths.
    parts_lower = {part.lower() for part in p.parts}
    if "appdata" in parts_lower:
        # Still validate with candidates when possible.
        for base in candidates:
            if _is_within(base, p):
                return True
        # If we couldn't validate, treat it as AppData anyway.
        return True

    for base in candidates:
        if _is_within(base, p):
            return True

    return False


def assert_not_appdata(
    path: str | Path,
    *,
    purpose: str,
    exception_cls: Type[Exception] = RuntimeError,
) -> None:
    if is_appdata_path(path):
        raise exception_cls(
            f"Refusing to use AppData path for {purpose}: {path}. "
            "AppData is reserved for UI state/logs/saves only; mods must live outside AppData."
        )
