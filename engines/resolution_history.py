from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class ResolutionHistoryEvent:
    evidence_hash: str
    conflict_type: str
    source: str
    file: str
    target: str
    mod_a: str
    mod_b: str
    action: str
    success: bool
    note: Optional[str] = None
    timestamp: Optional[str] = None

    def to_json(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp or _utc_now_iso(),
            "evidence_hash": self.evidence_hash,
            "conflict_type": self.conflict_type,
            "source": self.source,
            "file": self.file,
            "target": self.target,
            "mod_a": self.mod_a,
            "mod_b": self.mod_b,
            "action": self.action,
            "success": bool(self.success),
            "note": self.note or "",
        }


class ResolutionHistoryStore:
    """Append-only JSONL history. Minimal, durable, auditable."""

    def __init__(self, path: str):
        self.path = path

    def append(self, event: ResolutionHistoryEvent) -> None:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        rec = event.to_json()
        line = json.dumps(rec, ensure_ascii=False, sort_keys=True)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
