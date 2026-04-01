from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

import re


def _is_patch_mod_name(name: str) -> bool:
    try:
        return (name or "").lower().startswith("999_conflictpatch_")
    except Exception:
        return False


_ORDER_PREFIX_RE = re.compile(r"^(\d+)_")


def _order_value(mod: Any) -> int:
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


@dataclass(frozen=True)
class DetectedConflict:
    """Raw detected conflict before taxonomy/classification.

    This is intentionally close to what we have today (scan dicts + sim ConflictTrace).
    """

    source: str  # 'scan'|'sim'
    conflict_type: str
    file: str
    target: str
    mod_a: str
    mod_b: str
    kind: str = ""
    reason: str = ""
    payload: Any = None
    payload_dict: Optional[Dict[str, Any]] = None


def detect_conflicts(
    *,
    mods: Iterable[Any],
    sim_state: Optional[Any] = None,
    sim_conflicts: Optional[Iterable[Any]] = None,
) -> List[DetectedConflict]:
    mods_list = list(mods or [])
    by_name = {getattr(m, "name", ""): m for m in mods_list}

    out: List[DetectedConflict] = []

    # --- simulator-derived conflicts ---
    last = {}
    try:
        last = getattr(sim_state, "last_mut", {}) or {}
    except Exception:
        last = {}

    for ct in sim_conflicts or []:
        try:
            if _is_patch_mod_name(getattr(ct.first, "mod", "")) or _is_patch_mod_name(getattr(ct.second, "mod", "")):
                continue
            lm = last.get((ct.file, ct.xpath))
            if lm and _is_patch_mod_name(getattr(lm, "mod", "")):
                continue
        except Exception:
            pass

        kind = str(getattr(ct, "kind", "") or "")

        # Treat append-append as merge-safe in practice (both additive). We suppress it
        # so users don't see "conflicts" that don't require a winner.
        if kind == "append-append":
            continue

        # Anything that isn't a strict override is typically order-sensitive.
        # Map to load_order_priority so it can be resolved by reordering.
        ctype = "xml_override" if kind == "override" else "load_order_priority"

        out.append(
            DetectedConflict(
                source="sim",
                conflict_type=ctype,
                file=str(getattr(ct, "file", "") or ""),
                target=str(getattr(ct, "xpath", "") or ""),
                mod_a=str(getattr(ct.first, "mod", "") or ""),
                mod_b=str(getattr(ct.second, "mod", "") or ""),
                kind=kind,
                reason="",
                payload=ct,
            )
        )

    # --- scan-derived conflicts ---
    for m in mods_list:
        if getattr(m, "user_disabled", False):
            continue
        if _is_patch_mod_name(getattr(m, "name", "")):
            continue

        for c in getattr(m, "conflicts", None) or []:
            if not isinstance(c, dict):
                continue
            other = c.get("with")
            if not other:
                continue

            mod_a, mod_b = sorted(
                [getattr(m, "name", "") or "", str(other)],
                key=lambda s: (s or "").lower(),
            )

            file = str(c.get("file") or "")
            target = str(c.get("target") or "")
            ctype = str(c.get("conflict_type") or "")
            level = str(c.get("level") or "")
            reason = str(c.get("reason") or "")

            # Prefer simulator entries for xml override (only those have values for patching)
            if ctype.strip().lower() == "xml_override":
                continue

            # Derive overhaul-vs-standalone deterministically when one side is an overhaul
            ctype_eff = ctype
            try:
                other_mod = by_name.get(str(other))
                if other_mod and (
                    bool(getattr(m, "is_overhaul", False)) != bool(getattr(other_mod, "is_overhaul", False))
                ):
                    ctype_eff = "overhaul_vs_standalone"
            except Exception:
                pass

            payload = {"mod": getattr(m, "name", "") or ""}
            payload.update(c)

            # If a load-order conflict has a deterministic recommendation and current
            # order already satisfies it, suppress it so users don't see the same
            # "unresolved" conflict after applying a reorder.
            try:
                if str(ctype_eff or "").strip().lower() == "load_order_priority":
                    rf = str(payload.get("recommended_front") or "").strip()
                    rb = str(payload.get("recommended_back") or "").strip()
                    if rf and rb:
                        mf = by_name.get(rf)
                        mb = by_name.get(rb)
                        if mf is not None and mb is not None:
                            if _order_value(mf) < _order_value(mb):
                                continue
            except Exception:
                pass

            out.append(
                DetectedConflict(
                    source="scan",
                    conflict_type=ctype_eff,
                    file=file,
                    target=target,
                    mod_a=mod_a,
                    mod_b=mod_b,
                    kind=level,
                    reason=reason,
                    payload_dict=payload,
                )
            )

    return out
