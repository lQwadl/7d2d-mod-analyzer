from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional


class ConflictSource(str, Enum):
    scan = "scan"
    sim = "sim"


class Severity(str, Enum):
    info = "info"
    warning = "warning"
    error = "error"


@dataclass(frozen=True)
class ConflictEvidence:
    """Normalized evidence for a conflict.

    This is the stable shape we can hash and persist.
    """

    source: ConflictSource
    conflict_type: str
    file: str
    target: str
    mod_a: str
    mod_b: str
    kind: Optional[str] = None
    reason: Optional[str] = None


@dataclass
class Conflict:
    """Structured conflict used across engines.

    Keep UI compatibility via `to_unified_entry()`.
    """

    evidence_hash: str
    evidence: ConflictEvidence

    # Taxonomy/classification extras
    severity: Severity = Severity.warning
    taxonomy_error: Optional[str] = None

    # Resolution metadata
    resolvable: bool = False
    why_not: Optional[str] = None

    # Payload is optional raw details (sim ConflictTrace or scan dict)
    payload: Any = None

    # Optional extensibility
    provenance: Dict[str, Any] = field(default_factory=dict)

    def to_unified_entry(self) -> Dict[str, Any]:
        """Return the exact dict shape expected by the current GUI."""

        entry: Dict[str, Any] = {
            "source": self.evidence.source.value,
            "file": self.evidence.file or "",
            "target": self.evidence.target or "",
            "mod_a": self.evidence.mod_a or "",
            "mod_b": self.evidence.mod_b or "",
            "type": self.evidence.conflict_type or "log_only",
            "kind": self.evidence.kind or "",
            "resolvable": bool(self.resolvable),
            "why_not": self.why_not,
            "payload": self.payload,
        }
        if self.evidence.source == ConflictSource.scan:
            if isinstance(entry.get("payload"), dict):
                entry["payload"].setdefault("evidence_hash", self.evidence_hash)
                if self.taxonomy_error:
                    entry["payload"].setdefault("taxonomy_error", self.taxonomy_error)
            if self.evidence.reason:
                entry.setdefault("reason", self.evidence.reason)
        return entry


def conflicts_to_unified(conflicts: Iterable[Conflict]) -> List[Dict[str, Any]]:
    return [c.to_unified_entry() for c in (conflicts or [])]
