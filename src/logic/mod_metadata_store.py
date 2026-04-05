from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_METADATA_VERSION = 1


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_mod_id(folder_name: str) -> str:
    """Best-effort stable id from folder name.

    Strips __DISABLED__ prefix and leading NNN_ order prefix.
    """
    name = (folder_name or "").strip()
    if name.startswith("__DISABLED__"):
        name = name[len("__DISABLED__") :]
    if len(name) >= 4 and name[:3].isdigit() and name[3] == "_":
        name = name[4:]
    return name.strip() or (folder_name or "").strip()


def xml_signature(mod_path: Path) -> str:
    """Fast signature based on (relative path, mtime, size) for XML-ish files."""

    h = hashlib.sha256()

    def _add(p: Path) -> None:
        try:
            st = p.stat()
            rel = str(p.relative_to(mod_path)).replace("\\", "/").lower()
            h.update(rel.encode("utf-8", errors="ignore"))
            h.update(str(int(st.st_mtime)).encode("ascii", errors="ignore"))
            h.update(str(int(st.st_size)).encode("ascii", errors="ignore"))
        except Exception:
            return

    # All XML files (excluding ModInfo) + shader-ish evidence files
    for p in sorted(mod_path.rglob("*"), key=lambda x: str(x).lower()):
        try:
            if not p.is_file():
                continue
            nm = p.name.lower()
            if nm == "modinfo.xml":
                continue
            if (
                nm.endswith(".xml")
                or nm.endswith(".shader")
                or "shaders" in ("/" + str(p).lower().replace("\\", "/") + "/")
            ):
                _add(p)
        except Exception:
            continue

    return h.hexdigest()


def _boolish(v: Any) -> bool:
    try:
        if isinstance(v, bool):
            return v
        if isinstance(v, (int, float)):
            return bool(v)
        s = str(v or "").strip().lower()
        return s in {"1", "true", "yes", "y", "on"}
    except Exception:
        return False


@dataclass
class ModMetadata:
    mod_id: str
    signature: str
    categories: List[str]
    primary_category: str
    evidence: Dict[str, Any]
    last_scanned: str
    # User override / persisted flag (not derived from XML signature)
    is_framework: bool = False


class ModMetadataStore:
    def __init__(self, path: str):
        self.path = path
        self.data: Dict[str, Any] = {"version": _METADATA_VERSION, "mods": {}}
        self.load()

    def load(self) -> None:
        try:
            if not os.path.isfile(self.path):
                return
            with open(self.path, "r", encoding="utf-8") as f:
                self.data = json.load(f) or {"version": _METADATA_VERSION, "mods": {}}
        except Exception:
            self.data = {"version": _METADATA_VERSION, "mods": {}}

    def save(self) -> None:
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
        except Exception:
            return

    def get(self, mod_id: str) -> Optional[Dict[str, Any]]:
        try:
            mods = self.data.get("mods")
            if isinstance(mods, dict):
                return mods.get(mod_id)
        except Exception:
            pass
        return None

    def upsert(
        self,
        *,
        mod_id: str,
        signature: str,
        categories: List[str],
        primary_category: str,
        evidence: Optional[Dict[str, Any]] = None,
        is_framework: Optional[bool] = None,
    ) -> None:
        mods = self.data.setdefault("mods", {})
        if not isinstance(mods, dict):
            mods = {}
            self.data["mods"] = mods

        # Preserve user overrides across rescans unless explicitly updated.
        prev = mods.get(mod_id) if isinstance(mods.get(mod_id), dict) else {}
        prev_fw = None
        try:
            if isinstance(prev, dict):
                if "is_framework" in prev:
                    prev_fw = prev.get("is_framework")
                elif "isFramework" in prev:
                    prev_fw = prev.get("isFramework")
        except Exception:
            prev_fw = None

        mods[mod_id] = {
            "mod_id": mod_id,
            "signature": signature,
            "categories": list(categories or []),
            "primary_category": primary_category,
            "evidence": evidence or {},
            "last_scanned": _utc_now_iso(),
            # Store in snake_case but accept legacy camelCase when reading.
            "is_framework": _boolish(prev_fw) if is_framework is None else bool(is_framework),
        }

    def get_or_compute(
        self,
        *,
        folder_name: str,
        mod_path: str,
        compute_fn,
    ) -> ModMetadata:
        """Return cached metadata if signature matches; otherwise recompute via compute_fn."""

        mod_id = normalize_mod_id(folder_name)
        p = Path(mod_path)
        sig = xml_signature(p)

        cached = self.get(mod_id)
        if isinstance(cached, dict) and str(cached.get("signature") or "") == sig:
            cached_fw = False
            try:
                if "is_framework" in cached:
                    cached_fw = _boolish(cached.get("is_framework"))
                elif "isFramework" in cached:
                    cached_fw = _boolish(cached.get("isFramework"))
            except Exception:
                cached_fw = False
            return ModMetadata(
                mod_id=mod_id,
                signature=sig,
                categories=list(cached.get("categories") or []),
                primary_category=str(cached.get("primary_category") or "Miscellaneous"),
                evidence=dict(cached.get("evidence") or {}),
                last_scanned=str(cached.get("last_scanned") or ""),
                is_framework=bool(cached_fw),
            )

        categories, primary, evidence = compute_fn(p)
        # Preserve any existing framework flag on recompute.
        prev_fw = False
        try:
            if isinstance(cached, dict):
                if "is_framework" in cached:
                    prev_fw = _boolish(cached.get("is_framework"))
                elif "isFramework" in cached:
                    prev_fw = _boolish(cached.get("isFramework"))
        except Exception:
            prev_fw = False

        self.upsert(
            mod_id=mod_id,
            signature=sig,
            categories=categories,
            primary_category=primary,
            evidence=evidence,
            is_framework=prev_fw,
        )
        # best-effort persist; caller can also save once at end
        self.save()

        return ModMetadata(
            mod_id=mod_id,
            signature=sig,
            categories=categories,
            primary_category=primary,
            evidence=evidence,
            last_scanned=_utc_now_iso(),
            is_framework=bool(prev_fw),
        )

    def set_framework_flag(
        self,
        *,
        folder_name: str,
        mod_path: str = "",
        is_framework: bool,
    ) -> None:
        """Persist a user override for whether a mod is a framework.

        This is intentionally independent of the XML signature so rescans don't
        wipe the user's selection.
        """

        mod_id = normalize_mod_id(folder_name)
        cached = self.get(mod_id)

        signature = ""
        categories: List[str] = []
        primary = "Miscellaneous"
        evidence: Dict[str, Any] = {}

        try:
            if isinstance(cached, dict):
                signature = str(cached.get("signature") or "")
                categories = list(cached.get("categories") or [])
                primary = str(cached.get("primary_category") or primary)
                evidence = dict(cached.get("evidence") or {})
        except Exception:
            pass

        # If we have no signature yet but do have a path, compute a best-effort one.
        if (not signature) and mod_path:
            try:
                p = Path(mod_path)
                if p.is_dir():
                    signature = xml_signature(p)
            except Exception:
                signature = signature or ""

        self.upsert(
            mod_id=mod_id,
            signature=signature,
            categories=categories,
            primary_category=primary,
            evidence=evidence,
            is_framework=bool(is_framework),
        )
        self.save()
