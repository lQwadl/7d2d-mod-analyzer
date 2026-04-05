from __future__ import annotations

from typing import Any, Iterable, List

from engines.detection_engine import DetectedConflict
from engines.evidence import conflict_evidence_hash
from logic.conflict_taxonomy import normalize_conflict_type
from logic.target_formatter import format_target_display
from models.conflict import Conflict, ConflictEvidence, ConflictSource, Severity


def _default_severity(conflict_type: str, *, level_hint: str = "") -> Severity:
    ct = (conflict_type or "").strip().lower()
    lvl = (level_hint or "").strip().lower()

    if ct in {"missing_invalid", "duplicate_id", "missing_dependency", "deployment_access"}:
        return Severity.error
    if ct in {"world_compat", "poi_conflict"}:
        return Severity.error
    if lvl in {"error", "fatal"}:
        return Severity.error
    if lvl in {"warning", "warn"}:
        return Severity.warning
    return Severity.warning


def _resolvability(conflict_type: str, *, source: str) -> tuple[bool, str | None]:
    ct = (conflict_type or "").strip().lower()

    # MVP: keep existing GUI semantics
    if source == "sim":
        if ct == "xml_override":
            return True, None
        if ct == "load_order_priority":
            return True, None
        return False, f"Unsupported simulator kind: {ct}"

    supported = {"duplicate_id", "load_order_priority", "overhaul_vs_standalone", "asset_conflict"}
    if ct in supported:
        return True, None

    return (
        False,
        "Not auto-resolvable: destructive, world-breaking, or informational. Resolve manually (read details).",
    )


def classify_detected_conflicts(detected: Iterable[DetectedConflict]) -> List[Conflict]:
    out: List[Conflict] = []
    seen = set()

    for d in detected or []:
        kind = str(d.kind or "")
        file = str(d.file or "")
        target = str(d.target or "")

        ctype = str(d.conflict_type or "")
        taxonomy_error = None
        try:
            tx = normalize_conflict_type(
                conflict_type=ctype,
                file=file,
                level=kind,
                reason=d.reason,
            )
            ctype = tx.primary
            taxonomy_error = tx.classification_error
        except Exception:
            ctype = "log_only"
            taxonomy_error = "taxonomy normalization failed"

        mod_a = str(d.mod_a or "")
        mod_b = str(d.mod_b or "")

        sig = (ctype, file, target, mod_a, mod_b, str(d.source or ""))
        if d.source == "scan":
            # Deduplicate scan entries (mod list is symmetric)
            sig = (ctype, file, target, *sorted([mod_a, mod_b], key=lambda s: (s or "").lower()), "scan")
        if sig in seen:
            continue
        seen.add(sig)

        try:
            eh = conflict_evidence_hash(
                source=str(d.source or ""),
                conflict_type=ctype,
                file=file,
                target=target,
                mod_a=mod_a,
                mod_b=mod_b,
                kind=kind or None,
            )
        except Exception:
            eh = ""

        # Attach evidence hash on simulator payload for back-compat
        if d.source == "sim" and d.payload is not None:
            try:
                setattr(d.payload, "evidence_hash", eh)
                if taxonomy_error:
                    setattr(d.payload, "taxonomy_error", taxonomy_error)
            except Exception:
                pass

        resolvable, why_not = _resolvability(ctype, source=str(d.source or ""))

        payload: Any
        if d.source == "sim":
            payload = d.payload
        else:
            payload = d.payload_dict or {}
            if isinstance(payload, dict):
                if taxonomy_error:
                    payload.setdefault("taxonomy_error", taxonomy_error)
                payload.setdefault("evidence_hash", eh)

        # UI-friendly display label (keep stable `target` untouched for rules/hashes)
        try:
            td = format_target_display(file=file, target=target)
        except Exception:
            td = ""
        if td:
            if d.source == "sim" and payload is not None:
                try:
                    setattr(payload, "target_display", td)
                except Exception:
                    pass
            elif isinstance(payload, dict):
                payload.setdefault("target_display", td)

        evidence = ConflictEvidence(
            source=ConflictSource.sim if str(d.source) == "sim" else ConflictSource.scan,
            conflict_type=ctype,
            file=file,
            target=target,
            mod_a=mod_a,
            mod_b=mod_b,
            kind=kind or None,
            reason=d.reason or None,
        )

        out.append(
            Conflict(
                evidence_hash=eh,
                evidence=evidence,
                severity=_default_severity(ctype, level_hint=kind),
                taxonomy_error=taxonomy_error,
                resolvable=resolvable,
                why_not=why_not,
                payload=payload,
            )
        )

    return out
