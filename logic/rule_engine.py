from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

from logic.conflict_taxonomy import signature_for_rule_match
from logic.rule_store import Rule


@dataclass(frozen=True)
class RuleApplication:
    applied: bool
    rule_id: Optional[str] = None
    rule_type: Optional[str] = None
    reason: Optional[str] = None
    action: Optional[str] = None
    preferred: Optional[str] = None


class RuleEngine:
    """Deterministic rule engine.

    Precedence is strict and enforced by evaluation order:
      1) user rules
      2) profile rules
      3) learned rules (not implemented here)
      4) heuristics (fallback)

    This is intentionally separate from detection and learning.
    """

    def __init__(
        self,
        *,
        user_rules: Iterable[Rule] = (),
        profile_rules: Iterable[Rule] = (),
        learned_rules: Iterable[Rule] = (),
    ):
        self.user_rules = [r for r in (user_rules or []) if r.enabled]
        self.profile_rules = [r for r in (profile_rules or []) if r.enabled]
        self.learned_rules = [r for r in (learned_rules or []) if r.enabled]

    def apply_to_conflict_entry(self, entry: Dict[str, Any]) -> RuleApplication:
        """Return the highest-precedence matching rule for a unified conflict entry."""
        ct = (entry.get("type") or "").strip()
        file = (entry.get("file") or "").strip()
        target = (entry.get("target") or "").strip()
        a = (entry.get("mod_a") or "").strip()
        b = (entry.get("mod_b") or "").strip()

        sig = signature_for_rule_match(conflict_type=ct, file=file, target=target, mod_a=a, mod_b=b)

        for bucket_name, bucket in (
            ("user", self.user_rules),
            ("profile", self.profile_rules),
            ("learned", self.learned_rules),
        ):
            ra = self._match_bucket(bucket, sig=sig, entry=entry)
            if ra.applied:
                return ra

        return RuleApplication(applied=False)

    def _match_bucket(
        self,
        bucket: List[Rule],
        *,
        sig: Tuple[str, str, str, str, str],
        entry: Dict[str, Any],
    ) -> RuleApplication:
        ct, file, target, mod_a, mod_b = sig
        for r in bucket:
            # conflict match
            if r.conflict_type and str(r.conflict_type).strip().lower() != ct:
                continue
            if r.file and str(r.file).strip().lower() != file:
                continue
            if r.target and str(r.target).strip() != target:
                continue

            # mod match: if specified, must match the unordered pair
            if r.mod_a and r.mod_b:
                ra = str(r.mod_a).strip()
                rb = str(r.mod_b).strip()
                x, y = sorted([ra, rb], key=lambda s: s.lower())
                if (x.lower(), y.lower()) != (mod_a.lower(), mod_b.lower()):
                    continue

            # Apply rule semantics
            if r.type == "ignore_conflict":
                return RuleApplication(
                    applied=True,
                    rule_id=r.id,
                    rule_type=r.type,
                    action="ignore",
                    reason=r.note or "Ignored by rule",
                )

            if r.type == "always_win" and r.winner:
                preferred = str(r.winner).strip()
                return RuleApplication(
                    applied=True,
                    rule_id=r.id,
                    rule_type=r.type,
                    action="prefer",
                    preferred=preferred,
                    reason=r.note or f"Rule forces winner: {preferred}",
                )

            if r.type == "never_together" and r.mod_a and r.mod_b:
                return RuleApplication(
                    applied=True,
                    rule_id=r.id,
                    rule_type=r.type,
                    action="block",
                    reason=r.note or "Mods must never be loaded together",
                )

            if r.type == "disable_if_with" and r.loser:
                loser = str(r.loser).strip()
                return RuleApplication(
                    applied=True,
                    rule_id=r.id,
                    rule_type=r.type,
                    action="disable",
                    preferred=loser,
                    reason=r.note or f"Rule disables: {loser}",
                )

            if r.type in {"load_after", "load_before"}:
                return RuleApplication(
                    applied=True,
                    rule_id=r.id,
                    rule_type=r.type,
                    action=r.type,
                    reason=r.note or f"Rule: {r.type.replace('_', ' ')}",
                )

        return RuleApplication(applied=False)
