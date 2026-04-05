from __future__ import annotations

import os
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple


_ORDER_PREFIX_RE = re.compile(r"^(\d+)_")


def _norm_name(name: str) -> str:
    return (name or "").strip().lower()


def _safe_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except Exception:
        return int(default)


def current_order_value(mod: Any) -> int:
    """Best-effort current load order (lower loads earlier)."""

    try:
        lo = getattr(mod, "load_order", None)
        if isinstance(lo, int):
            return int(lo)
    except Exception:
        pass
    try:
        name = str(getattr(mod, "name", "") or "")
        if name.startswith("__DISABLED__"):
            name = name[len("__DISABLED__") :]
        m = _ORDER_PREFIX_RE.match(name)
        if m:
            return int(m.group(1))
    except Exception:
        pass
    return 10_000_000


def _parse_required_mods_from_modinfo(modinfo_path: Path) -> List[str]:
    """Extract RequiredMod/Dependency-like fields from ModInfo.xml.

    This is best-effort and intentionally tolerant.
    """

    try:
        tree = ET.parse(str(modinfo_path))
        root = tree.getroot()
    except Exception:
        return []

    out: List[str] = []
    for e in root.iter():
        try:
            tag = (e.tag or "").strip().lower()
        except Exception:
            tag = ""
        if tag not in {"requiredmod", "dependencymod", "dependencymods", "dependency", "depend"}:
            continue
        try:
            v = (e.attrib or {}).get("value") or (e.attrib or {}).get("name") or (e.attrib or {}).get("mod")
        except Exception:
            v = None
        if v:
            out.append(str(v).strip())
    return [x for x in out if x]


def compute_dependency_graph(mods: Sequence[Any]) -> Dict[str, Set[str]]:
    """Return mod_name -> set(required_mod_name-ish).

    Keys/values are folder-like names (not normalized ids), because 7DTD dependencies
    are often written as ModInfo Name-ish strings. We do best-effort matching later.
    """

    by_name = {str(getattr(m, "name", "") or ""): m for m in (mods or [])}
    out: Dict[str, Set[str]] = {n: set() for n in by_name.keys()}

    for name, m in by_name.items():
        try:
            modinfo = Path(str(getattr(m, "path", "") or "")) / "ModInfo.xml"
            if not modinfo.is_file():
                continue
            req = _parse_required_mods_from_modinfo(modinfo)
            for r in req:
                if r:
                    out[name].add(r)
        except Exception:
            continue

    return out


def _tier_score(mod: Any) -> int:
    """Higher score == should win (load later) when in doubt."""

    # Existing project tiers already encode "frameworks first" etc.
    tier = str(getattr(mod, "tier", "") or "").strip()
    if not tier:
        tier = str(getattr(mod, "priority", "") or "").strip()

    # Map to a coarse score where Patch Mods/Overhauls win, frameworks win over content.
    # (We want deterministic behavior; exact values are not critical.)
    t = tier.lower()
    if "patch" in t:
        return 100
    if "overhaul" in t:
        return 90
    if "core" in t or "framework" in t or "api" in t or "backend" in t or "library" in t:
        return 80
    if "weapon framework" in t:
        return 70
    if "content" in t or "gameplay" in t or "world" in t or "poi" in t:
        return 50
    if "ui" in t or "visual" in t or "audio" in t or "presentation" in t:
        return 30
    if "qol" in t or "utility" in t:
        return 40
    return 45


def _category_score(mod: Any) -> int:
    # Categories come from mod_metadata.json + XML-driven detection.
    cats = list(getattr(mod, "categories", None) or [])
    primary = str(getattr(mod, "category", "") or "")
    all_txt = " ".join([primary] + [str(c) for c in cats]).lower()

    if any(k in all_txt for k in ["core", "framework", "library", "harmony", "api"]):
        return 20
    if any(k in all_txt for k in ["overhaul"]):
        return 15
    if any(k in all_txt for k in ["ui", "xui", "hud", "cosmetic"]):
        return -10
    return 0


def priority_score(mod: Any) -> int:
    """Return a deterministic priority score.

    Higher means "prefer to win" (load later) for conflicts.
    """

    score = 0
    try:
        score += _tier_score(mod)
    except Exception:
        score += 0
    try:
        score += _category_score(mod)
    except Exception:
        pass
    try:
        if bool(getattr(mod, "is_overhaul", False)):
            score += 10
    except Exception:
        pass
    return int(score)


def _dep_match(required: str, candidate_name: str) -> bool:
    r = _norm_name(required)
    c = _norm_name(candidate_name)
    if not r or not c:
        return False
    # Exact or substring match is common in ModInfo.xml.
    return (r == c) or (r in c) or (c in r)


def _is_dependency_of(
    deps: Dict[str, Set[str]],
    *,
    dependent: str,
    maybe_dependency: str,
) -> bool:
    reqs = deps.get(dependent) or set()
    for r in reqs:
        if _dep_match(r, maybe_dependency):
            return True
    return False


@dataclass(frozen=True)
class WinnerDecision:
    # front loads earlier; back loads later (wins)
    front: str
    back: str
    reason: str


def decide_winner(
    mods: Sequence[Any],
    *,
    mod_a_name: str,
    mod_b_name: str,
    conflict_type: str,
    file: str = "",
    target: str = "",
    deps: Optional[Dict[str, Set[str]]] = None,
) -> WinnerDecision:
    """Choose a deterministic winner for a conflict.

    - For 7DTD style "last loaded wins", the winner is `back`.
    - Dependencies are always loaded before dependents.
    - Then priority score decides.
    - Finally fall back to preserving current order, then name.
    """

    by_name = {str(getattr(m, "name", "") or ""): m for m in (mods or [])}
    a = by_name.get(mod_a_name)
    b = by_name.get(mod_b_name)
    deps = deps or {}

    # Dependency rule: dep must load before dependent
    try:
        if _is_dependency_of(deps, dependent=mod_a_name, maybe_dependency=mod_b_name):
            return WinnerDecision(
                front=mod_b_name, back=mod_a_name, reason="Dependency ordering: dependency loads first."
            )
        if _is_dependency_of(deps, dependent=mod_b_name, maybe_dependency=mod_a_name):
            return WinnerDecision(
                front=mod_a_name, back=mod_b_name, reason="Dependency ordering: dependency loads first."
            )
    except Exception:
        pass

    # Overhaul guidance
    try:
        if a is not None and b is not None:
            oa = bool(getattr(a, "is_overhaul", False))
            ob = bool(getattr(b, "is_overhaul", False))
            if oa != ob:
                if oa:
                    return WinnerDecision(
                        front=mod_b_name, back=mod_a_name, reason="Overhaul should load after standalone mods."
                    )
                return WinnerDecision(
                    front=mod_a_name, back=mod_b_name, reason="Overhaul should load after standalone mods."
                )
    except Exception:
        pass

    # Priority score (tier/category)
    try:
        if a is not None and b is not None:
            sa = priority_score(a)
            sb = priority_score(b)
            if sa != sb:
                if sa > sb:
                    return WinnerDecision(
                        front=mod_b_name,
                        back=mod_a_name,
                        reason=f"Priority score: {mod_a_name} ({sa}) > {mod_b_name} ({sb}).",
                    )
                return WinnerDecision(
                    front=mod_a_name,
                    back=mod_b_name,
                    reason=f"Priority score: {mod_b_name} ({sb}) > {mod_a_name} ({sa}).",
                )
    except Exception:
        pass

    # Preserve current winner
    try:
        if a is not None and b is not None:
            loa = current_order_value(a)
            lob = current_order_value(b)
            if loa != lob:
                if loa > lob:
                    return WinnerDecision(
                        front=mod_b_name,
                        back=mod_a_name,
                        reason="Preserving current winner (higher load_order loads later).",
                    )
                return WinnerDecision(
                    front=mod_a_name,
                    back=mod_b_name,
                    reason="Preserving current winner (higher load_order loads later).",
                )
    except Exception:
        pass

    # Final fallback by name
    if _norm_name(mod_a_name) <= _norm_name(mod_b_name):
        return WinnerDecision(
            front=mod_a_name, back=mod_b_name, reason="No strong signal; deterministic fallback by name."
        )
    return WinnerDecision(front=mod_b_name, back=mod_a_name, reason="No strong signal; deterministic fallback by name.")


def build_conflict_map(unified_conflicts: Sequence[Dict[str, Any]]) -> Dict[str, List[str]]:
    """Return file -> sorted list of mods involved (best-effort)."""

    m: Dict[str, Set[str]] = {}
    for e in unified_conflicts or []:
        try:
            file = str(e.get("file") or "").strip()
            if not file:
                continue
            a = str(e.get("mod_a") or "").strip()
            b = str(e.get("mod_b") or "").strip()
            s = m.setdefault(file, set())
            if a:
                s.add(a)
            if b:
                s.add(b)
        except Exception:
            continue
    out: Dict[str, List[str]] = {}
    for k, v in m.items():
        out[k] = sorted(v, key=lambda s: (s or "").lower())
    return out
