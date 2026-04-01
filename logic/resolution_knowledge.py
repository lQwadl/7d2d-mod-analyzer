import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


def _utc_now_iso(now: Optional[datetime] = None) -> str:
    dt = now or datetime.now(timezone.utc)
    return dt.replace(microsecond=0).isoformat()


def _confidence(success_count: int, applied_count: int) -> float:
    if applied_count <= 0:
        return 0.0
    return float(success_count) / float(applied_count)


@dataclass
class ResolutionOption:
    conflict_type: str
    resolution_id: str
    label: str
    tier: str  # 'common'|'uncommon'
    applied_count: int
    success_count: int
    risky: bool
    last_used: Optional[str]
    disabled: bool

    @property
    def confidence(self) -> float:
        return _confidence(self.success_count, self.applied_count)


class ResolutionKnowledgeBase:
    """Experience-based resolution knowledge.

    Stores common/uncommon strategies per conflict type and tracks success/failure.

    Learning rules (MVP):
    - Promote: uncommon resolution with success_count >= 3 -> common
    - Demote: common resolution with applied_count >= 3 and confidence < 0.34 -> mark risky
    """

    def __init__(self, path: str, now: Optional[datetime] = None):
        self.path = path
        self._now = now
        self.data: Dict[str, Any] = {"version": 2, "conflict_types": {}}
        self.load()

    def _ensure_parent_dir(self) -> None:
        parent = os.path.dirname(self.path)
        if parent:
            os.makedirs(parent, exist_ok=True)

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
            self.data.setdefault("version", 1)
            self.data.setdefault("conflict_types", {})
            before = self._normalized_json()
            self._migrate_if_needed()
            self.compact()
            after = self._normalized_json()
            if before != after:
                # Automatically persist upgraded/compacted data.
                self._save_normalized_json(after)
        except Exception:
            self.data = {"version": 2, "conflict_types": {}}

    def _migrate_if_needed(self) -> None:
        """Best-effort forward migration for older KB files.

        Versioning is intentionally lightweight; we avoid breaking older files.
        """
        try:
            v = int(self.data.get("version") or 1)
        except Exception:
            v = 1

        if v < 2:
            # v2 introduces optional `disabled` on resolution entries.
            # No structural changes required; we just bump the version.
            self.data["version"] = 2

    def save(self) -> None:
        # Keep the file tidy and de-duplicated.
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

    def _get_ct_entry(self, conflict_type: str) -> Dict[str, Any]:
        cts = self.data.setdefault("conflict_types", {})
        ct = (conflict_type or "unknown").strip()
        entry = cts.get(ct)
        if not isinstance(entry, dict):
            entry = {
                "common_resolutions": [],
                "uncommon_resolutions": [],
                "last_used": None,
            }
            cts[ct] = entry
        entry.setdefault("common_resolutions", [])
        entry.setdefault("uncommon_resolutions", [])
        entry.setdefault("last_used", None)
        return entry

    def list_options(self, conflict_type: str, *, include_disabled: bool = False) -> List[ResolutionOption]:
        entry = self._get_ct_entry(conflict_type)
        out: List[ResolutionOption] = []

        def _read(arr: Any, tier: str) -> None:
            if not isinstance(arr, list):
                return
            for r in arr:
                if not isinstance(r, dict):
                    continue
                rid = str(r.get("id") or "").strip()
                if not rid:
                    continue
                disabled = bool(r.get("disabled", False))
                if disabled and not include_disabled:
                    continue
                out.append(
                    ResolutionOption(
                        conflict_type=conflict_type,
                        resolution_id=rid,
                        label=str(r.get("label") or rid),
                        tier=tier,
                        applied_count=int(r.get("applied_count") or 0),
                        success_count=int(r.get("success_count") or 0),
                        risky=bool(r.get("risky", False)),
                        last_used=r.get("last_used"),
                        disabled=disabled,
                    )
                )

        _read(entry.get("common_resolutions"), "common")
        _read(entry.get("uncommon_resolutions"), "uncommon")

        # sort: common first, then confidence desc, then applied desc
        out.sort(
            key=lambda o: (
                o.tier != "common",
                o.disabled,
                o.risky,
                -o.confidence,
                -o.applied_count,
                o.label.lower(),
            )
        )
        return out

    def _merge_resolution_arrays(self, entry: Dict[str, Any]) -> Tuple[List[dict], List[dict]]:
        """Merge duplicate resolution IDs across tiers and remove redundant fields."""

        def _as_list(x: Any) -> List[dict]:
            return [r for r in x if isinstance(r, dict)] if isinstance(x, list) else []

        merged: Dict[str, dict] = {}

        def _merge_one(r: dict, *, tier: str) -> None:
            rid = str(r.get("id") or "").strip()
            if not rid:
                return

            m = merged.get(rid)
            if not isinstance(m, dict):
                m = {
                    "id": rid,
                    "label": str(r.get("label") or rid),
                    "applied_count": 0,
                    "success_count": 0,
                    "risky": False,
                    "disabled": False,
                    "last_used": None,
                    "tier": tier,
                }
                merged[rid] = m

            # Aggregate counts (duplicates are redundant; keep the combined history)
            try:
                m["applied_count"] = int(m.get("applied_count") or 0) + int(r.get("applied_count") or 0)
            except Exception:
                pass
            try:
                m["success_count"] = int(m.get("success_count") or 0) + int(r.get("success_count") or 0)
            except Exception:
                pass

            # Prefer a more descriptive label
            try:
                lbl = str(r.get("label") or "").strip()
                if lbl and (not m.get("label") or len(lbl) > len(str(m.get("label") or ""))):
                    m["label"] = lbl
            except Exception:
                pass

            # Union flags
            m["risky"] = bool(m.get("risky", False)) or bool(r.get("risky", False))
            m["disabled"] = bool(m.get("disabled", False)) or bool(r.get("disabled", False))

            # Keep the most recent last_used if both exist (ISO sorts lexicographically)
            lu = r.get("last_used")
            if isinstance(lu, str) and lu:
                prev = m.get("last_used")
                if not isinstance(prev, str) or lu > prev:
                    m["last_used"] = lu

            # Tier preference: common wins
            if tier == "common":
                m["tier"] = "common"

        for r in _as_list(entry.get("common_resolutions")):
            _merge_one(r, tier="common")
        for r in _as_list(entry.get("uncommon_resolutions")):
            _merge_one(r, tier="uncommon")

        # Auto-disable consistently bad strategies (keeps history but removes noise)
        for m in merged.values():
            try:
                applied = int(m.get("applied_count") or 0)
                success = int(m.get("success_count") or 0)
                conf = _confidence(success, applied)
                if applied >= 8 and conf < 0.25:
                    m["disabled"] = True
                if applied >= 5 and success == 0 and bool(m.get("risky", False)):
                    m["disabled"] = True
            except Exception:
                pass

        common_out: List[dict] = []
        uncommon_out: List[dict] = []
        for m in merged.values():
            rid = str(m.get("id") or "").strip()
            if not rid:
                continue
            out = {
                "id": rid,
                "label": str(m.get("label") or rid),
                "applied_count": int(m.get("applied_count") or 0),
                "success_count": int(m.get("success_count") or 0),
            }
            if bool(m.get("risky", False)):
                out["risky"] = True
            if bool(m.get("disabled", False)):
                out["disabled"] = True
            if isinstance(m.get("last_used"), str) and m.get("last_used"):
                out["last_used"] = m.get("last_used")

            if m.get("tier") == "common":
                common_out.append(out)
            else:
                uncommon_out.append(out)

        # Stable ordering: common first, then non-disabled, then confidence desc
        def _sort_key(r: dict) -> tuple:
            applied = int(r.get("applied_count") or 0)
            success = int(r.get("success_count") or 0)
            conf = _confidence(success, applied)
            return (
                bool(r.get("disabled", False)),
                bool(r.get("risky", False)),
                -conf,
                -applied,
                str(r.get("label") or r.get("id") or "").lower(),
            )

        common_out.sort(key=_sort_key)
        uncommon_out.sort(key=_sort_key)
        return common_out, uncommon_out

    def compact(self) -> None:
        """Remove redundant information and keep KB deterministic.

        - De-duplicate resolution IDs across common/uncommon tiers
        - Merge duplicate counts
        - Auto-disable consistently failing strategies
        - Drop empty conflict types with no information
        """
        cts = self.data.get("conflict_types")
        if not isinstance(cts, dict):
            self.data["conflict_types"] = {}
            return

        new_cts: Dict[str, Any] = {}
        for ct, entry in cts.items():
            if not isinstance(entry, dict):
                continue

            common, uncommon = self._merge_resolution_arrays(entry)
            last_used = entry.get("last_used")
            if not common and not uncommon and not last_used:
                continue

            new_entry: Dict[str, Any] = {
                "common_resolutions": common,
                "uncommon_resolutions": uncommon,
                "last_used": last_used if isinstance(last_used, str) else None,
            }
            new_cts[str(ct)] = new_entry

        self.data["conflict_types"] = new_cts

    def record_attempt(self, *, conflict_type: str, resolution_id: str, success: bool) -> None:
        entry = self._get_ct_entry(conflict_type)
        now_iso = _utc_now_iso(self._now)

        def _find(arr: List[dict]) -> Optional[dict]:
            for r in arr:
                if isinstance(r, dict) and str(r.get("id") or "").strip() == resolution_id:
                    return r
            return None

        common = entry.get("common_resolutions")
        uncommon = entry.get("uncommon_resolutions")
        if not isinstance(common, list):
            common = []
            entry["common_resolutions"] = common
        if not isinstance(uncommon, list):
            uncommon = []
            entry["uncommon_resolutions"] = uncommon

        target = _find(common) or _find(uncommon)
        if target is None:
            # unknown resolution id: treat as uncommon by default
            target = {
                "id": resolution_id,
                "label": resolution_id,
                "applied_count": 0,
                "success_count": 0,
                "risky": True,
            }
            uncommon.append(target)

        target["applied_count"] = int(target.get("applied_count") or 0) + 1
        if success:
            target["success_count"] = int(target.get("success_count") or 0) + 1
        target["last_used"] = now_iso
        entry["last_used"] = now_iso

        # Learning rules
        self._apply_learning_rules(entry, resolution_id)

        # Always compact the touched conflict type to remove redundant entries.
        try:
            common_out, uncommon_out = self._merge_resolution_arrays(entry)
            entry["common_resolutions"] = common_out
            entry["uncommon_resolutions"] = uncommon_out
        except Exception:
            pass

    def _apply_learning_rules(self, entry: Dict[str, Any], resolution_id: str) -> None:
        common = entry.get("common_resolutions")
        uncommon = entry.get("uncommon_resolutions")
        if not isinstance(common, list) or not isinstance(uncommon, list):
            return

        # Promote uncommon -> common
        promote_idx = None
        for i, r in enumerate(uncommon):
            if not isinstance(r, dict):
                continue
            if str(r.get("id") or "").strip() != resolution_id:
                continue
            if int(r.get("success_count") or 0) >= 3:
                promote_idx = i
                break
        if promote_idx is not None:
            r = uncommon.pop(promote_idx)
            try:
                r["risky"] = False
            except Exception:
                pass
            common.append(r)

        # Demote common by marking risky (do not move tiers in MVP)
        for r in common:
            if not isinstance(r, dict):
                continue
            if str(r.get("id") or "").strip() != resolution_id:
                continue
            applied = int(r.get("applied_count") or 0)
            success = int(r.get("success_count") or 0)
            conf = _confidence(success, applied)
            if applied >= 3 and conf < 0.34:
                r["risky"] = True

    def best_option(self, conflict_type: str) -> Optional[ResolutionOption]:
        opts = self.list_options(conflict_type)
        return opts[0] if opts else None
