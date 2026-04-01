from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from engines.classification_engine import classify_detected_conflicts
from engines.detection_engine import detect_conflicts
from models.conflict import Conflict, conflicts_to_unified


def build_structured_conflicts(
    *,
    mods: Iterable[Any],
    sim_state: Optional[Any] = None,
    sim_conflicts: Optional[Iterable[Any]] = None,
) -> List[Conflict]:
    """Return structured conflicts (engine-layer canonical model)."""

    detected = detect_conflicts(mods=mods, sim_state=sim_state, sim_conflicts=sim_conflicts)
    return classify_detected_conflicts(detected)


def build_unified_conflicts(
    *,
    mods: Iterable[Any],
    sim_state: Optional[Any] = None,
    sim_conflicts: Optional[Iterable[Any]] = None,
) -> List[Dict[str, Any]]:
    """Build the Resolve Conflicts unified list while remaining UI-shape compatible.

    Output dict shape intentionally matches the existing GUI entries:
      - source,file,target,mod_a,mod_b,type,kind,resolvable,why_not,payload,reason

    We do *not* add new top-level keys.
    Evidence hashes are attached as:
      - scan entries: payload['evidence_hash']
      - sim entries: setattr(payload, 'evidence_hash', ...)
    """

    structured = build_structured_conflicts(mods=mods, sim_state=sim_state, sim_conflicts=sim_conflicts)
    return conflicts_to_unified(structured)
