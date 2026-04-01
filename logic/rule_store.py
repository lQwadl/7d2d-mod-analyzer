from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Rule:
    id: str
    type: str  # load_after, load_before, never_together, always_win, disable_if_with, ignore_conflict
    enabled: bool = True

    # Matching
    conflict_type: Optional[str] = None
    file: Optional[str] = None
    target: Optional[str] = None

    mod_a: Optional[str] = None
    mod_b: Optional[str] = None

    # Action fields
    winner: Optional[str] = None  # always_win
    loser: Optional[str] = None  # disable_if_with

    note: str = ""

    origin: str = "user"  # user | profile | learned
    created_at: float = field(default_factory=lambda: float(time.time()))
    updated_at: float = field(default_factory=lambda: float(time.time()))


DEFAULT_STORE = {
    "version": 1,
    "active_profile": "default",
    "rules": [],
    "profiles": {
        "default": {
            "rules": [],
        }
    },
}


class RuleStore:
    """Persistent rule store.

    Precedence is enforced by the rule engine (user > profile > learned > heuristics).
    This store keeps user rules and per-profile rules.
    """

    def __init__(self, path: str):
        self.path = path
        self.data: Dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        if not os.path.exists(self.path):
            self.data = json.loads(json.dumps(DEFAULT_STORE))
            self._save()
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        except Exception:
            self.data = json.loads(json.dumps(DEFAULT_STORE))

        # Migrate minimal fields
        self.data.setdefault("version", 1)
        self.data.setdefault("active_profile", "default")
        self.data.setdefault("rules", [])
        self.data.setdefault("profiles", {"default": {"rules": []}})
        if "default" not in self.data["profiles"]:
            self.data["profiles"]["default"] = {"rules": []}

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)

    def save(self) -> None:
        self._save()

    def active_profile(self) -> str:
        return str(self.data.get("active_profile") or "default")

    def set_active_profile(self, name: str) -> None:
        name = (name or "default").strip() or "default"
        self.data["active_profile"] = name
        self.data.setdefault("profiles", {})
        self.data["profiles"].setdefault(name, {"rules": []})
        self._save()

    def list_user_rules(self) -> List[Rule]:
        out = []
        for r in self.data.get("rules") or []:
            try:
                out.append(Rule(**r))
            except Exception:
                continue
        return out

    def list_profile_rules(self, profile: Optional[str] = None) -> List[Rule]:
        profile = (profile or self.active_profile()).strip() or "default"
        prof = (self.data.get("profiles") or {}).get(profile) or {"rules": []}
        out = []
        for r in prof.get("rules") or []:
            try:
                out.append(Rule(**r))
            except Exception:
                continue
        return out

    def add_rule(self, rule: Rule, *, to_profile: bool = False) -> Rule:
        rule.updated_at = float(time.time())
        if not rule.id:
            rule.id = str(uuid.uuid4())

        if to_profile:
            prof = self.active_profile()
            self.data.setdefault("profiles", {})
            self.data["profiles"].setdefault(prof, {"rules": []})
            self.data["profiles"][prof]["rules"].append(asdict(rule))
        else:
            self.data.setdefault("rules", [])
            self.data["rules"].append(asdict(rule))

        self._save()
        return rule

    def disable_rule(self, rule_id: str) -> None:
        rid = (rule_id or "").strip()
        if not rid:
            return

        changed = False

        for r in self.data.get("rules") or []:
            if str(r.get("id")) == rid:
                r["enabled"] = False
                r["updated_at"] = float(time.time())
                changed = True

        for prof, pdata in (self.data.get("profiles") or {}).items():
            for r in pdata.get("rules") or []:
                if str(r.get("id")) == rid:
                    r["enabled"] = False
                    r["updated_at"] = float(time.time())
                    changed = True

        if changed:
            self._save()
