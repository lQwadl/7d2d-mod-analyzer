"""Script-style tests for enabled-state filtering in logic.conflict_detector.

Run:
  python tests/conflict_detector_enabled_filter_test.py
"""

import os

# Ensure project root is importable when running as a script
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from logic.conflict_detector import detect_conflicts


class _Mod:
    def __init__(self, name: str):
        self.name = name
        self.enabled = True
        self.user_disabled = False
        self.disabled = False
        self.is_overhaul = False
        self.load_order = 0
        self.conflicts = []
        self.semantic_edits = []
        self.xml_targets = {}


def _any_conflicts(mods):
    return any((getattr(m, "conflicts", []) or []) for m in mods)


def main():
    a = _Mod("ModA")
    b = _Mod("ModB")

    a.xml_targets = {"items.xml": {'/items/item[@name="x"]'}}
    b.xml_targets = {"items.xml": {'/items/item[@name="x"]'}}

    detect_conflicts([a, b])
    assert _any_conflicts([a, b]), "expected conflict when both mods enabled"

    # Disable via enabled=False (authoritative)
    b.enabled = False
    detect_conflicts([a, b])
    assert not _any_conflicts([a, b]), (
        "expected no conflicts when one mod enabled=False"
    )

    # Disable via user_disabled=True
    b.enabled = True
    b.user_disabled = True
    detect_conflicts([a, b])
    assert not _any_conflicts([a, b]), (
        "expected no conflicts when one mod user_disabled=True"
    )

    print("PASS")


if __name__ == "__main__":
    main()
