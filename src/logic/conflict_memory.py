import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple, List

_DISABLED_PREFIX = "__DISABLED__"
_ORDER_PREFIX_RE = re.compile(r"^(\d+)_")

_MEMORY_VERSION = 2
_MAX_EXACT_PER_PAIR_TYPE = 30
_MAX_LIST_ITEMS = 500


def _utc_today_iso(now: Optional[datetime] = None) -> str:
    dt = now or datetime.now(timezone.utc)
    return dt.date().isoformat()


def normalize_mod_id(mod_folder_name: str) -> str:
    """Best-effort stable id derived from folder name.

    Strips `__DISABLED__` and a leading `NNN_` order prefix.
    """
    name = (mod_folder_name or "").strip()
    if name.startswith(_DISABLED_PREFIX):
        name = name[len(_DISABLED_PREFIX) :]
    m = _ORDER_PREFIX_RE.match(name)
    if m:
        name = name[len(m.group(0)) :]
    return name.strip()


def _pair_key(mod_a: str, mod_b: str) -> Tuple[str, str]:
    a = normalize_mod_id(mod_a)
    b = normalize_mod_id(mod_b)
    return tuple(sorted([a, b], key=lambda s: s.lower()))  # type: ignore


def _conflict_key(mod_a: str, mod_b: str, conflict_type: str, file: str = "", target: str = "") -> str:
    a, b = _pair_key(mod_a, mod_b)
    ct = (conflict_type or "unknown").strip()
    f = (file or "").strip()
    t = (target or "").strip()
    return f"{a}||{b}||{ct}||{f}||{t}".lower()


def _coarse_conflict_key(mod_a: str, mod_b: str, conflict_type: str) -> str:
    a, b = _pair_key(mod_a, mod_b)
    ct = (conflict_type or "unknown").strip()
    return f"{a}||{b}||{ct}".lower()


@dataclass
class Recommendation:
    action: str  # e.g. 'patch', 'disable', 'reorder', 'set_order', 'disable_standalone'
    preferred_mod_id: Optional[str] = None  # normalized
    order_value: Optional[int] = None
    confidence: float = 0.0
    applied_count: int = 0
    success_count: int = 0
    last_seen: Optional[str] = None
    note: Optional[str] = None


class ConflictMemory:
    """Lightweight persistent conflict memory.

    Stores:
    - per-mod metadata
    - per mod-pair conflict outcomes and preferred resolutions
    - per-category aggregate patterns

    This module is intentionally deterministic and safe (no side effects beyond JSON IO).
    """

    def __init__(self, path: str, now: Optional[datetime] = None):
        self.path = path
        self._now = now
        self.data: Dict[str, Any] = {
            "version": _MEMORY_VERSION,
            "mods": {},
            "pairs": {},
            "categories": {},
        }
        self.load()

    def _migrate_if_needed(self) -> None:
        """Best-effort forward migration for older CKB files."""
        try:
            v = int(self.data.get("version") or 1)
        except Exception:
            v = 1
        if v < 2:
            # v2 adds a deterministic compaction pass; no breaking schema changes.
            self.data["version"] = 2

    def _dedupe_list(self, v: Any) -> List[str]:
        if not isinstance(v, list):
            return []
        out: List[str] = []
        seen = set()
        for x in v:
            s = str(x or "").strip()
            if not s:
                continue
            k = s.lower()
            if k in seen:
                continue
            seen.add(k)
            out.append(s)
            if len(out) >= _MAX_LIST_ITEMS:
                break
        return out

    def _canonical_coarse_key(self, a_id: str, b_id: str, conflict_type: str) -> str:
        a = (a_id or "").strip()
        b = (b_id or "").strip()
        ct = (conflict_type or "unknown").strip()
        mods = sorted([a, b], key=lambda s: s.lower())
        return f"{mods[0]}||{mods[1]}||{ct}".lower()

    def _canonical_exact_key(self, a_id: str, b_id: str, conflict_type: str, file: str, target: str) -> str:
        a = (a_id or "").strip()
        b = (b_id or "").strip()
        ct = (conflict_type or "unknown").strip()
        f = (file or "").strip()
        t = (target or "").strip()
        mods = sorted([a, b], key=lambda s: s.lower())
        return f"{mods[0]}||{mods[1]}||{ct}||{f}||{t}".lower()

    def _parse_pair_key(self, key: str) -> Optional[Tuple[str, ...]]:
        try:
            parts = str(key or "").split("||")
            if len(parts) not in (3, 5):
                return None
            return tuple(p.strip() for p in parts)
        except Exception:
            return None

    def compact(self) -> None:
        """Remove redundant/noisy information while preserving aggregate learning.

        - Canonicalize/merge pair keys (case/order differences)
        - Ensure coarse entries exist when exact entries exist
        - Drop exact entries with empty file+target (redundant with coarse)
        - Cap exact entries per pair+type to avoid unbounded growth
        - Dedupe and cap per-mod/per-category lists
        """
        self._migrate_if_needed()

        # ---- mods ----
        mods = self.data.get("mods")
        if not isinstance(mods, dict):
            mods = {}
            self.data["mods"] = mods

        for mid, m in list(mods.items()):
            if not isinstance(m, dict):
                mods.pop(mid, None)
                continue
            m["mod_id"] = str(m.get("mod_id") or mid)
            m["category"] = str(m.get("category") or "")
            m["is_overhaul"] = bool(m.get("is_overhaul", False))
            m["known_conflicts"] = self._dedupe_list(m.get("known_conflicts"))
            m["safe_with"] = self._dedupe_list(m.get("safe_with"))
            m["unsafe_with"] = self._dedupe_list(m.get("unsafe_with"))

            # If a mod is both safe+unsafe with another, unsafe wins.
            try:
                unsafe = {s.lower() for s in (m.get("unsafe_with") or [])}
                m["safe_with"] = [s for s in (m.get("safe_with") or []) if s.lower() not in unsafe]
            except Exception:
                pass

        # ---- categories ----
        cats = self.data.get("categories")
        if not isinstance(cats, dict):
            cats = {}
            self.data["categories"] = cats
        for k, ce in list(cats.items()):
            if not isinstance(ce, dict):
                cats.pop(k, None)
                continue
            ce["category"] = str(ce.get("category") or k)
            ce["high_risk"] = bool(ce.get("high_risk", False))
            ce["common_conflicts"] = self._dedupe_list(ce.get("common_conflicts"))

        # ---- pairs ----
        pairs = self.data.get("pairs")
        if not isinstance(pairs, dict):
            pairs = {}
            self.data["pairs"] = pairs

        # First pass: canonicalize keys and merge duplicates
        merged: Dict[str, dict] = {}

        def _merge_entry(dst: dict, src: dict) -> dict:
            # Merge counts
            try:
                dst["applied_count"] = int(dst.get("applied_count") or 0) + int(src.get("applied_count") or 0)
            except Exception:
                pass
            try:
                dst["success_count"] = int(dst.get("success_count") or 0) + int(src.get("success_count") or 0)
            except Exception:
                pass

            # Pick a consistent action/preferred
            if src.get("resolution_action") and not dst.get("resolution_action"):
                dst["resolution_action"] = src.get("resolution_action")
            if src.get("preferred_mod_id") and not dst.get("preferred_mod_id"):
                dst["preferred_mod_id"] = src.get("preferred_mod_id")
            if src.get("order_value") is not None and dst.get("order_value") is None:
                dst["order_value"] = src.get("order_value")

            # Most recent last_seen (ISO date compares lexicographically)
            lu = src.get("last_seen")
            if isinstance(lu, str) and lu:
                prev = dst.get("last_seen")
                if not isinstance(prev, str) or lu > prev:
                    dst["last_seen"] = lu

            # Prefer longer note
            try:
                n1 = str(dst.get("note") or "")
                n2 = str(src.get("note") or "")
                if len(n2) > len(n1):
                    dst["note"] = n2
            except Exception:
                pass

            return dst

        for k, v in list(pairs.items()):
            if not isinstance(v, dict):
                continue
            parts = self._parse_pair_key(k)

            # If the key is parseable, canonicalize it.
            if parts and len(parts) == 3:
                a, b, ct = parts
                ck = self._canonical_coarse_key(a, b, ct)
            elif parts and len(parts) == 5:
                a, b, ct, f, t = parts
                ck = self._canonical_exact_key(a, b, ct, f, t)
            else:
                # Keep unknown keys as-is (best effort)
                ck = str(k)

            cur = merged.get(ck)
            if not isinstance(cur, dict):
                merged[ck] = dict(v)
            else:
                merged[ck] = _merge_entry(cur, v)

        # Second pass: group exact entries under coarse keys, ensure coarse exists, and cap exacts
        new_pairs: Dict[str, dict] = {}
        groups: Dict[str, List[Tuple[str, dict]]] = {}

        for k, v in merged.items():
            parts = self._parse_pair_key(k)
            if not parts:
                # Unknown: preserve
                new_pairs[k] = v
                continue

            if len(parts) == 3:
                # Coarse
                new_pairs[k] = v
                continue

            # Exact
            a, b, ct, f, t = parts
            if not (str(f or "").strip() or str(t or "").strip()):
                # Exact with no file/target is redundant with coarse
                continue

            coarse_k = self._canonical_coarse_key(a, b, ct)
            groups.setdefault(coarse_k, []).append((k, v))

        # Build coarse if missing, then add capped exacts
        for coarse_k, exacts in groups.items():
            coarse = new_pairs.get(coarse_k)
            if not isinstance(coarse, dict):
                # Create coarse aggregate from exacts
                total_applied = 0
                total_success = 0
                best = None
                best_applied = -1
                last_seen = None
                for _, ex in exacts:
                    try:
                        a = int(ex.get("applied_count") or 0)
                        s = int(ex.get("success_count") or 0)
                        total_applied += a
                        total_success += s
                        if a > best_applied:
                            best = ex
                            best_applied = a
                        lu = ex.get("last_seen")
                        if isinstance(lu, str) and (not isinstance(last_seen, str) or lu > last_seen):
                            last_seen = lu
                    except Exception:
                        continue

                coarse = {
                    "mods": list((best or {}).get("mods") or []),
                    "conflict_type": (best or {}).get("conflict_type") or "unknown",
                    "resolution_action": (best or {}).get("resolution_action") or "unknown",
                    "preferred_mod_id": (best or {}).get("preferred_mod_id"),
                    "applied_count": int(total_applied),
                    "success_count": int(total_success),
                    "last_seen": last_seen,
                }
                new_pairs[coarse_k] = coarse

            # Deduplicate exacts by (file,target)
            best_by_ft: Dict[str, Tuple[str, dict]] = {}

            def _exact_score(ex: dict) -> tuple:
                try:
                    applied = int(ex.get("applied_count") or 0)
                except Exception:
                    applied = 0
                lu = ex.get("last_seen")
                lu_s = lu if isinstance(lu, str) else ""
                return (applied, lu_s)

            for k, ex in exacts:
                f = str(ex.get("file") or "").strip().lower()
                t = str(ex.get("target") or "").strip().lower()
                ft = f"{f}||{t}"
                prev = best_by_ft.get(ft)
                if prev is None or _exact_score(ex) > _exact_score(prev[1]):
                    best_by_ft[ft] = (k, ex)

            deduped = list(best_by_ft.values())
            deduped.sort(
                key=lambda kv: (_exact_score(kv[1])[0], _exact_score(kv[1])[1]),
                reverse=True,
            )

            for k, ex in deduped[:_MAX_EXACT_PER_PAIR_TYPE]:
                new_pairs[k] = ex

        self.data["pairs"] = new_pairs

    def load(self) -> None:
        try:
            if not os.path.exists(self.path):
                self._ensure_parent_dir()
                self.save()
                return
            with open(self.path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                self.data.update(loaded)
            # basic shape hardening
            self.data.setdefault("version", 1)
            self.data.setdefault("mods", {})
            self.data.setdefault("pairs", {})
            self.data.setdefault("categories", {})
            before = self._normalized_json()
            self._migrate_if_needed()
            self.compact()
            after = self._normalized_json()
            if before != after:
                # Automatically persist upgraded/compacted data.
                self._save_normalized_json(after)
        except Exception:
            # Corrupt or unreadable file: keep in-memory defaults.
            self.data = {
                "version": _MEMORY_VERSION,
                "mods": {},
                "pairs": {},
                "categories": {},
            }

    def save(self) -> None:
        try:
            self._migrate_if_needed()
            self.compact()
        except Exception:
            pass
        self._ensure_parent_dir()
        self._save_normalized_json()

    def _normalized_json(self) -> str:
        try:
            return json.dumps(self.data, sort_keys=True, separators=(",", ":"))
        except Exception:
            return ""

    def _save_normalized_json(self, normalized: Optional[str] = None) -> None:
        self._ensure_parent_dir()
        tmp = self.path + ".tmp"
        if normalized is None:
            normalized = self._normalized_json()
        with open(tmp, "w", encoding="utf-8") as f:
            # Write the compact form (no indentation) to keep diffs small and deterministic.
            f.write(normalized)
        os.replace(tmp, self.path)

    def _ensure_parent_dir(self) -> None:
        parent = os.path.dirname(self.path)
        if parent:
            os.makedirs(parent, exist_ok=True)

    def get_recommendation(
        self,
        *,
        mod_a: str,
        mod_b: str,
        conflict_type: str,
        file: str = "",
        target: str = "",
    ) -> Optional[Recommendation]:
        pairs = self.data.get("pairs", {}) or {}
        exact = pairs.get(_conflict_key(mod_a, mod_b, conflict_type, file, target))
        coarse = pairs.get(_coarse_conflict_key(mod_a, mod_b, conflict_type))
        entry = exact or coarse
        if not isinstance(entry, dict):
            return None

        applied = int(entry.get("applied_count") or 0)
        success = int(entry.get("success_count") or 0)
        conf = (success / applied) if applied > 0 else 0.0

        return Recommendation(
            action=str(entry.get("resolution_action") or "").strip() or "unknown",
            preferred_mod_id=str(entry.get("preferred_mod_id") or "").strip() or None,
            order_value=(int(entry["order_value"]) if isinstance(entry.get("order_value"), int) else None),
            confidence=conf,
            applied_count=applied,
            success_count=success,
            last_seen=entry.get("last_seen"),
            note=entry.get("note"),
        )

    def record_resolution(
        self,
        *,
        mod_a: str,
        mod_b: str,
        category_a: Optional[str],
        category_b: Optional[str],
        conflict_type: str,
        file: str,
        target: str,
        resolution_action: str,
        preferred_mod_name: Optional[str],
        successful: bool,
        order_value: Optional[int] = None,
        note: Optional[str] = None,
    ) -> None:
        today = _utc_today_iso(self._now)

        a_id = normalize_mod_id(mod_a)
        b_id = normalize_mod_id(mod_b)
        preferred_id = normalize_mod_id(preferred_mod_name) if preferred_mod_name else None

        # --- per-mod ---
        for mid, cat, other in ((a_id, category_a, b_id), (b_id, category_b, a_id)):
            mods = self.data.setdefault("mods", {})
            m = mods.get(mid)
            if not isinstance(m, dict):
                m = {
                    "mod_id": mid,
                    "category": cat or "",
                    "is_overhaul": False,
                    "known_conflicts": [],
                    "safe_with": [],
                    "unsafe_with": [],
                    "last_seen": today,
                }
                mods[mid] = m

            if cat and not m.get("category"):
                m["category"] = cat

            m["last_seen"] = today

            kc = m.setdefault("known_conflicts", [])
            if isinstance(kc, list) and conflict_type and conflict_type not in kc:
                kc.append(conflict_type)

            key = "safe_with" if successful else "unsafe_with"
            arr = m.setdefault(key, [])
            if isinstance(arr, list) and other and other not in arr:
                arr.append(other)

        # --- per-pair ---
        pairs = self.data.setdefault("pairs", {})
        exact_key = _conflict_key(mod_a, mod_b, conflict_type, file, target)
        coarse_key = _coarse_conflict_key(mod_a, mod_b, conflict_type)

        existing = pairs.get(exact_key)
        if not isinstance(existing, dict):
            # Start both exact + coarse if missing. Coarse aggregates across targets.
            existing = {
                "mods": sorted([a_id, b_id], key=lambda s: s.lower()),
                "conflict_type": conflict_type,
                "file": file,
                "target": target,
                "resolution_action": resolution_action,
                "preferred_mod_id": preferred_id,
                "applied_count": 0,
                "success_count": 0,
                "last_seen": today,
                "order_value": order_value,
                "note": note,
            }
            pairs[exact_key] = existing

        existing["applied_count"] = int(existing.get("applied_count") or 0) + 1
        if successful:
            existing["success_count"] = int(existing.get("success_count") or 0) + 1
        existing["last_seen"] = today
        existing["resolution_action"] = resolution_action
        if preferred_id:
            existing["preferred_mod_id"] = preferred_id
        if order_value is not None:
            existing["order_value"] = int(order_value)
        if note:
            existing["note"] = str(note)

        # Coarse aggregate
        coarse = pairs.get(coarse_key)
        if not isinstance(coarse, dict):
            coarse = {
                "mods": sorted([a_id, b_id], key=lambda s: s.lower()),
                "conflict_type": conflict_type,
                "resolution_action": resolution_action,
                "preferred_mod_id": preferred_id,
                "applied_count": 0,
                "success_count": 0,
                "last_seen": today,
            }
            pairs[coarse_key] = coarse

        coarse["applied_count"] = int(coarse.get("applied_count") or 0) + 1
        if successful:
            coarse["success_count"] = int(coarse.get("success_count") or 0) + 1
        coarse["last_seen"] = today
        coarse["resolution_action"] = resolution_action
        if preferred_id:
            coarse["preferred_mod_id"] = preferred_id

        # --- category patterns (very simple MVP) ---
        cats = self.data.setdefault("categories", {})
        for cat in (category_a, category_b):
            if not cat:
                continue
            ce = cats.get(cat)
            if not isinstance(ce, dict):
                ce = {
                    "category": cat,
                    "high_risk": False,
                    "common_conflicts": [],
                    "last_seen": today,
                }
                cats[cat] = ce
            ce["last_seen"] = today
            cc = ce.setdefault("common_conflicts", [])
            if isinstance(cc, list) and conflict_type and conflict_type not in cc:
                cc.append(conflict_type)
            # Mark high risk if we see error-grade classes often
            if conflict_type in {"xml_override", "duplicate_id", "exclusive"}:
                ce["high_risk"] = True

    def confidence_for_pair(
        self,
        *,
        mod_a: str,
        mod_b: str,
        conflict_type: str,
        file: str = "",
        target: str = "",
    ) -> float:
        rec = self.get_recommendation(
            mod_a=mod_a,
            mod_b=mod_b,
            conflict_type=conflict_type,
            file=file,
            target=target,
        )
        return rec.confidence if rec else 0.0
