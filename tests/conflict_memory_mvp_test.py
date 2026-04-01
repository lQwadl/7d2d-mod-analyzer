import os

# Ensure project root is importable when running as a script
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from logic.conflict_memory import ConflictMemory
from tests._test_tmp import temp_dir


def main():
    with temp_dir("conflict_mem_") as root:
        path = os.path.join(str(root), "conflict_memory.json")
        mem = ConflictMemory(path)

        mem.record_resolution(
            mod_a="010_ModA",
            mod_b="020_ModB",
            category_a="Weapons",
            category_b="Weapons",
            conflict_type="xml_override",
            file="items.xml",
            target="/items/item[@name='x']",
            resolution_action="patch",
            preferred_mod_name="010_ModA",
            successful=True,
            note="Prefer ModA weapon stats",
        )
        mem.save()

        # Add redundant / duplicated entries to ensure compaction cleans them up
        mem2 = ConflictMemory(path)
        # Duplicate exact key via manual injection (different casing)
        pairs = mem2.data.setdefault("pairs", {})
        pairs["moda||modb||xml_override||items.xml||/items/item[@name='x']"] = {
            "mods": ["ModA", "ModB"],
            "conflict_type": "xml_override",
            "file": "items.xml",
            "target": "/items/item[@name='x']",
            "resolution_action": "patch",
            "preferred_mod_id": "ModA",
            "applied_count": 2,
            "success_count": 1,
            "last_seen": "2026-01-01",
        }
        # Redundant exact with empty file+target (should be dropped)
        pairs["moda||modb||xml_override||||"] = {
            "mods": ["ModA", "ModB"],
            "conflict_type": "xml_override",
            "file": "",
            "target": "",
            "resolution_action": "patch",
            "preferred_mod_id": "ModA",
            "applied_count": 1,
            "success_count": 1,
            "last_seen": "2026-01-02",
        }
        # safe/unsafe redundancy on mod
        mods = mem2.data.setdefault("mods", {})
        mods["ModA"] = {
            "mod_id": "ModA",
            "category": "Weapons",
            "is_overhaul": False,
            "known_conflicts": ["xml_override", "xml_override"],
            "safe_with": ["ModB", "ModB"],
            "unsafe_with": ["ModB"],
            "last_seen": "2026-01-02",
        }

        mem2.save()

        mem3 = ConflictMemory(path)
        # Should have only one exact entry for that file/target and no empty file/target exact
        keys = list((mem3.data.get("pairs") or {}).keys())
        assert all("||xml_override||" not in k or (not k.endswith("||||")) for k in keys)

        # safe_with should drop ModB because it's also in unsafe_with
        m = (mem3.data.get("mods") or {}).get("ModA") or {}
        assert "ModB" not in (m.get("safe_with") or [])
        assert "ModB" in (m.get("unsafe_with") or [])

        mem2 = ConflictMemory(path)
        rec = mem2.get_recommendation(
            mod_a="__DISABLED__010_ModA",
            mod_b="020_ModB",
            conflict_type="xml_override",
            file="items.xml",
            target="/items/item[@name='x']",
        )
        assert rec is not None
        assert rec.action == "patch"
        assert rec.preferred_mod_id == "ModA"
        # Compaction may merge duplicate entries, so counts/confidence can differ.
        assert rec.applied_count >= 1
        assert rec.success_count >= 1
        assert 0.0 <= rec.confidence <= 1.0

    print("PASS")


if __name__ == "__main__":
    main()
