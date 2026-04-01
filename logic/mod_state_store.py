from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional


@dataclass
class ModState:
    enabled: bool = True
    user_disabled: bool = False


class ModStateStore:
    """Authoritative per-install enabled state.

    Stored as JSON mapping install_id -> {enabled, user_disabled}.
    """

    def __init__(self, path: str | Path = "mods_state.json"):
        self.path = Path(path)
        self._data: Dict[str, ModState] = {}
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            self._data = {}
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            self._data = {}
            return
        if not isinstance(raw, dict):
            self._data = {}
            return

        out: Dict[str, ModState] = {}
        for k, v in raw.items():
            if not isinstance(k, str) or not k.strip():
                continue
            if not isinstance(v, dict):
                continue
            enabled = bool(v.get("enabled", True))
            user_disabled = bool(v.get("user_disabled", (not enabled)))
            # User-disabled implies not enabled.
            if user_disabled:
                enabled = False
            out[k.strip().lower()] = ModState(enabled=enabled, user_disabled=user_disabled)
        self._data = out

    def save(self) -> None:
        payload = {k: {"enabled": st.enabled, "user_disabled": st.user_disabled} for k, st in sorted(self._data.items())}
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def get(self, install_id: str) -> Optional[ModState]:
        if not install_id:
            return None
        return self._data.get(install_id.strip().lower())

    def set(self, install_id: str, *, enabled: bool, user_disabled: bool) -> None:
        if not install_id or not str(install_id).strip():
            raise ValueError("install_id required")
        iid = str(install_id).strip().lower()
        enabled = bool(enabled)
        user_disabled = bool(user_disabled)
        if user_disabled:
            enabled = False
        self._data[iid] = ModState(enabled=enabled, user_disabled=user_disabled)

    def set_enabled(self, install_id: str, enabled: bool) -> None:
        self.set(install_id, enabled=enabled, user_disabled=(not bool(enabled)))

    def items(self):
        return self._data.items()
