from pathlib import Path

from logic.category_policy import normalize_category
from logic.load_order_engine import infer_semantic_impact, infer_tier
from logic.xml_category_classifier import detect_categories_for_mod


def classify_mod(mod):
    """Assign deterministic XML-derived categories to a mod object.

    Hard rule: folder names and prefixes must never override XML-based categorization.
    """

    try:
        cats, primary, evidence = detect_categories_for_mod(Path(getattr(mod, "path", "") or ""))
    except Exception:
        cats, primary, evidence = (["Miscellaneous"], "Miscellaneous", {})

    try:
        mod.categories = list(cats or [])
    except Exception:
        pass

    try:
        mod.category = normalize_category(primary)
    except Exception:
        mod.category = primary or "Miscellaneous"

    try:
        mod.category_evidence = dict(evidence or {})
    except Exception:
        pass

    # Load order is computed by the rule-based engine (no numeric scoring).
    try:
        mod.tier = infer_tier(mod)
        mod.semantic_impact = infer_semantic_impact(mod)
    except Exception:
        pass

    try:
        mod.is_overhaul = bool("Overhauls" in (mod.categories or []))
    except Exception:
        pass
