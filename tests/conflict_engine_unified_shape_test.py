"""Script-style tests for ConflictEngine unified conflict emission.

Run:
  python tests/conflict_engine_unified_shape_test.py
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engines.conflict_engine import build_unified_conflicts
from mock_deploy.mutation import ConflictTrace, Mutation


class _Mod:
    def __init__(
        self, name: str, *, is_overhaul: bool = False, user_disabled: bool = False
    ):
        self.name = name
        self.is_overhaul = is_overhaul
        self.user_disabled = user_disabled
        self.conflicts = []


def main():
    # scan conflicts
    a = _Mod("010_ModA", is_overhaul=False)
    b = _Mod("020_ModB", is_overhaul=True)
    a.conflicts.append(
        {
            "level": "error",
            "file": "items.xml",
            "target": "/items/item[@name='x']",
            "with": b.name,
            "reason": "Both mods modify same id",
            "conflict_type": "duplicate_id",
        }
    )

    # sim conflicts
    first = Mutation(
        mod=a.name,
        file="items.xml",
        xpath="/configs/item[@name='x']",
        op="set",
        value="A",
        order=1,
    )
    second = Mutation(
        mod=b.name,
        file="items.xml",
        xpath="/configs/item[@name='x']",
        op="set",
        value="B",
        order=2,
    )
    ct = ConflictTrace(
        xpath=first.xpath, file=first.file, first=first, second=second, kind="override"
    )

    class _State:
        def __init__(self):
            self.last_mut = {}

    state = _State()

    unified = build_unified_conflicts(mods=[a, b], sim_state=state, sim_conflicts=[ct])

    # Ensure required keys exist and no crashes
    assert unified, "expected at least one unified conflict"
    for e in unified:
        for k in (
            "source",
            "file",
            "target",
            "mod_a",
            "mod_b",
            "type",
            "kind",
            "resolvable",
            "payload",
        ):
            assert k in e, f"missing key: {k}"

    sim_entries = [e for e in unified if e.get("source") == "sim"]
    assert sim_entries, "expected simulator entries"
    assert getattr(sim_entries[0]["payload"], "evidence_hash", ""), (
        "sim payload should get evidence_hash attribute"
    )

    scan_entries = [e for e in unified if e.get("source") == "scan"]
    assert scan_entries, "expected scan entries"
    p = scan_entries[0].get("payload")
    assert isinstance(p, dict)
    assert p.get("evidence_hash"), "scan payload should include evidence_hash"

    # Overhaul vs standalone derivation
    assert scan_entries[0].get("type") == "overhaul_vs_standalone"

    print("PASS")


if __name__ == "__main__":
    main()
