from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Optional

from logic.conflict_memory import ConflictMemory
from logic.resolution_knowledge import ResolutionKnowledgeBase
from models.conflict import Conflict


@dataclass(frozen=True)
class MemoryRecommendation:
    action: str
    preferred_mod_id: Optional[str]
    confidence: float
    order_value: Optional[int] = None
    note: Optional[str] = None


class MemoryEngine:
    """Facade over ConflictMemory + ResolutionKnowledgeBase.

    This is a *thin* wrapper intended for Phase 1 separation.
    """

    def __init__(
        self,
        *,
        conflict_memory_path: str = os.path.join("data", "conflict_memory.json"),
        resolution_kb_path: str = os.path.join("data", "resolution_knowledge.json"),
    ):
        self.conflict_memory = ConflictMemory(conflict_memory_path)
        self.resolution_kb = ResolutionKnowledgeBase(resolution_kb_path)

    def recommend(self, conflict: Conflict) -> Optional[MemoryRecommendation]:
        """Return a memory-backed recommendation for a conflict."""
        if not conflict:
            return None

        try:
            rec = self.conflict_memory.get_recommendation(
                mod_a=conflict.evidence.mod_a,
                mod_b=conflict.evidence.mod_b,
                conflict_type=conflict.evidence.conflict_type,
                file=conflict.evidence.file,
                target=conflict.evidence.target,
            )
        except Exception:
            return None

        if not rec or not getattr(rec, "action", None) or rec.action == "unknown":
            return None

        try:
            order_value = getattr(rec, "order_value", None)
            if order_value is not None:
                order_value = int(order_value)
        except Exception:
            order_value = None

        return MemoryRecommendation(
            action=str(rec.action),
            preferred_mod_id=(str(rec.preferred_mod_id) if rec.preferred_mod_id else None),
            confidence=float(getattr(rec, "confidence", 0.0) or 0.0),
            order_value=order_value,
            note=(str(rec.note) if getattr(rec, "note", None) else None),
        )

    def save(self) -> None:
        try:
            self.conflict_memory.save()
        except Exception:
            pass
        try:
            self.resolution_kb.save()
        except Exception:
            pass
