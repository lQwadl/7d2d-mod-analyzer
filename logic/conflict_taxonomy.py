from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Tuple

# Authoritative primary conflict types (no "unknown")
PRIMARY_TYPES = {
    "missing_invalid",
    "duplicate_id",
    "overhaul_vs_standalone",
    "xml_override",
    "load_order_priority",
    "redundant",
    "asset_conflict",
    "poi_conflict",
    "world_compat",
    "performance",
    "log_only",
    "missing_dependency",
    "deployment_access",
}


# Legacy / alternate keys -> primary
ALIASES = {
    "missing": "missing_invalid",
    "invalid": "missing_invalid",
    "no_modinfo": "missing_invalid",
    "invalid_xml": "missing_invalid",
    "wrong_depth": "missing_invalid",
    "case_mismatch": "missing_invalid",
    "exclusive": "xml_override",  # legacy internal; treated as xml override risk
    "merge": "load_order_priority",
    "override": "xml_override",
}


WORLD_BREAKING_FILES = {
    "rwgmixer.xml",
    "prefabs.xml",
    "worldglobal.xml",
    "biomes.xml",
}


@dataclass(frozen=True)
class TaxonomyResult:
    primary: str
    secondary_tag: Optional[str] = None
    classification_error: Optional[str] = None


def _norm(s: Any) -> str:
    try:
        return str(s or "").strip()
    except Exception:
        return ""


def normalize_conflict_type(
    *,
    conflict_type: Any,
    file: Any = None,
    level: Any = None,
    reason: Any = None,
) -> TaxonomyResult:
    """Return a deterministic primary conflict type.

    This function never returns "unknown". If classification fails, it falls back
    to 'log_only' and reports a classification_error for audit.
    """

    ct = _norm(conflict_type).lower()
    lvl = _norm(level).lower()
    f = _norm(file).lower()

    if not ct:
        # Infer from level/file hints
        if lvl in {"error", "fatal"}:
            # Missing/invalid is the safest "block" bucket when we can't classify
            return TaxonomyResult(
                "missing_invalid",
                classification_error="missing conflict_type at error level",
            )
        if f in WORLD_BREAKING_FILES:
            return TaxonomyResult(
                "world_compat",
                classification_error="missing conflict_type on world file",
            )
        return TaxonomyResult("log_only", classification_error="missing conflict_type")

    ct = ALIASES.get(ct, ct)

    if ct in PRIMARY_TYPES:
        return TaxonomyResult(ct)

    # File-based inference as a last resort
    if f in WORLD_BREAKING_FILES:
        return TaxonomyResult(
            "world_compat",
            classification_error=f"unrecognized conflict_type '{ct}' on world file",
        )

    # Default: informational
    return TaxonomyResult("log_only", classification_error=f"unrecognized conflict_type '{ct}'")


def is_save_breaking(*, conflict_type: str, file: str) -> bool:
    """Hard gate: actions that can break saves/worlds should require confirmation."""
    try:
        ct = (conflict_type or "").strip().lower()
        f = (file or "").strip().lower()
        if ct in {"poi_conflict", "world_compat"}:
            return True
        return f in WORLD_BREAKING_FILES
    except Exception:
        return False


def signature_for_rule_match(
    *,
    conflict_type: str,
    file: str,
    target: str,
    mod_a: str,
    mod_b: str,
) -> Tuple[str, str, str, str, str]:
    """Deterministic key used by the rule engine for matching."""
    ct = _norm(conflict_type).lower()
    f = _norm(file).lower()
    t = _norm(target)
    a = _norm(mod_a)
    b = _norm(mod_b)
    ma, mb = sorted([a, b], key=lambda s: s.lower())
    return ct, f, t, ma, mb
