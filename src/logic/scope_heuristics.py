from __future__ import annotations

from typing import Any, Iterable, Tuple


def _semantic_keys(mod: Any) -> set[Tuple[str, str]]:
    keys: set[Tuple[str, str]] = set()
    edits = getattr(mod, "semantic_edits", None)
    if not isinstance(edits, list) or not edits:
        return keys

    for e in edits:
        if not isinstance(e, dict):
            continue
        file = str(e.get("file") or "").strip().lower()
        target = str(e.get("target") or "").strip()
        if file and target:
            keys.add((file, target))

    return keys


def _file_keys(mod: Any) -> set[str]:
    files = getattr(mod, "xml_files", None)
    if not isinstance(files, (set, list, tuple)):
        return set()
    out = set()
    for f in files:
        s = str(f or "").strip().lower()
        if s:
            out.add(s)
    return out


def overlap_evidence(mod_a: Any, mod_b: Any) -> tuple[str, list[str]]:
    """Return (kind, sample_list) for evidence overlap.

    - kind == 'semantic' if both mods have semantic_edits and overlap on (file,target)
    - kind == 'files' for overlap on xml_files (fallback)
    - kind == 'none' if no evidence overlap
    """

    a_sem = _semantic_keys(mod_a)
    b_sem = _semantic_keys(mod_b)
    if a_sem and b_sem:
        overlap = a_sem.intersection(b_sem)
        if overlap:
            samples = [f"{f}:{t}" for (f, t) in sorted(overlap)[:6]]
            return "semantic", samples
        return "none", []

    a_files = _file_keys(mod_a)
    b_files = _file_keys(mod_b)
    overlap_files = a_files.intersection(b_files)
    if overlap_files:
        samples = [s for s in sorted(overlap_files)[:10]]
        return "files", samples

    return "none", []


def has_any_overlap(mod_a: Any, mod_b: Any) -> bool:
    kind, _samples = overlap_evidence(mod_a, mod_b)
    return kind != "none"


def filter_overlapping_mods(base_mod: Any, others: Iterable[Any]) -> tuple[list[Any], str, list[str]]:
    """Filter `others` down to those that overlap with `base_mod`.

    Returns (overlapping_mods, evidence_kind, evidence_samples)
    where evidence_kind/samples are aggregated across overlaps.
    """

    overlapping = []
    kinds = []
    samples_out: list[str] = []

    for o in others:
        if o is base_mod:
            continue
        kind, samples = overlap_evidence(base_mod, o)
        if kind == "none":
            continue
        overlapping.append(o)
        kinds.append(kind)
        for s in samples:
            if s not in samples_out:
                samples_out.append(s)
                if len(samples_out) >= 10:
                    break

    # Prefer semantic if any pair had it
    evidence_kind = "semantic" if "semantic" in kinds else ("files" if "files" in kinds else "none")
    return overlapping, evidence_kind, samples_out
