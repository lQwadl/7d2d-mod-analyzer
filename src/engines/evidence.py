import hashlib
import json
from typing import Any, Dict, Optional

from logic.conflict_memory import normalize_mod_id


def _stable_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def conflict_evidence_hash(
    *,
    source: str,
    conflict_type: str,
    file: str,
    target: str,
    mod_a: str,
    mod_b: str,
    kind: Optional[str] = None,
) -> str:
    """Return a deterministic evidence hash for a conflict.

    Notes:
    - Order-independent across mod_a/mod_b.
    - Normalizes mod ids (strips __DISABLED__ and numeric prefixes).
    - Only uses fields we already have today.
    """
    a = normalize_mod_id(mod_a or "")
    b = normalize_mod_id(mod_b or "")
    mods = sorted([a, b], key=lambda s: (s or "").lower())

    payload: Dict[str, Any] = {
        "source": str(source or ""),
        "type": str(conflict_type or "unknown"),
        "file": str(file or ""),
        "target": str(target or ""),
        "mods": mods,
    }
    if kind:
        payload["kind"] = str(kind)

    raw = _stable_json(payload).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()
