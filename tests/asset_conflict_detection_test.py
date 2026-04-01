"""Script-style test for asset overlap -> asset_conflict detection.

Run:
  python tests/asset_conflict_detection_test.py
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from logic.conflict_detector import detect_conflicts


class Mod:
    def __init__(self, name: str, asset_files=None):
        self.name = name
        self.enabled = True
        self.user_disabled = False
        self.disabled = False
        self.is_patch = False
        self.is_overhaul = False
        self.load_order = 100
        self.conflicts = []

        self.systems = set()
        self.xml_files = set()
        self.xml_targets = {}
        self.semantic_edits = []
        self.asset_files = set(asset_files or [])


def main():
    a = Mod("A", asset_files={"textures/weapons/pipepistol.dds", "sounds/gunshot.wav"})
    b = Mod("B", asset_files={"textures/weapons/pipepistol.dds"})

    detect_conflicts([a, b])

    c = next((c for c in a.conflicts if c.get("conflict_type") == "asset_conflict"), None)
    assert c is not None, a.conflicts
    assert c.get("file") == "assets", c
    assert str(c.get("target") or "").startswith("asset:"), c

    print("PASS")


if __name__ == "__main__":
    main()
