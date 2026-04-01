"""End-to-end-ish script test for Duplicate ID resolution (disable-by-rename).

Creates two mods that trigger a scan-detected `duplicate_id` conflict (via heuristic xml_targets
in core definition file names), then disables one mod folder and verifies the conflict disappears
on the next conflict detection pass.

Run:
  python tests/resolve_disable_duplicate_id_test.py
"""

import os
import sys
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from logic.resolve_actions import disable_mod_folder
from models.mod import Mod
from scanner.xml_analyzer import analyze_xml
from logic.conflict_detector import detect_conflicts
from tests._test_tmp import temp_dir


def _write_items_xml(mod_dir: Path, quality_value: str) -> None:
    cfg = mod_dir / "Config"
    cfg.mkdir(parents=True, exist_ok=True)

    # IMPORTANT: no xpath-based patch ops here; we want heuristic target extraction
    # to trigger `duplicate_id` on core definition files.
    (cfg / "items.xml").write_text(
        f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<items>
  <item name=\"x\">
    <property name=\"Quality\" value=\"{quality_value}\" />
  </item>
</items>
""",
        encoding="utf-8",
    )

    (mod_dir / "ModInfo.xml").write_text(
        """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<xml><ModInfo><Name value=\"X\"/></ModInfo></xml>
""",
        encoding="utf-8",
    )


def main():
    with temp_dir("dup_id_") as tmp_root:
        mods_root = tmp_root / "Mods"
        mods_root.mkdir(parents=True, exist_ok=True)

        mod_a_dir = mods_root / "010_ModA"
        mod_b_dir = mods_root / "020_ModB"
        mod_a_dir.mkdir(parents=True, exist_ok=True)
        mod_b_dir.mkdir(parents=True, exist_ok=True)

        _write_items_xml(mod_a_dir, "A")
        _write_items_xml(mod_b_dir, "B")

        mod_a = Mod(mod_a_dir.name, str(mod_a_dir))
        mod_b = Mod(mod_b_dir.name, str(mod_b_dir))

        analyze_xml(mod_a)
        analyze_xml(mod_b)

        detect_conflicts([mod_a, mod_b])

        # Verify we got a duplicate_id conflict
        all_conflicts = (mod_a.conflicts or []) + (mod_b.conflicts or [])
        if not any(c.get("conflict_type") == "duplicate_id" for c in all_conflicts):
            raise SystemExit(f"Expected duplicate_id conflict, got: {all_conflicts}")

        # Disable ModB via the same mechanism as the Resolve UI (rename prefix)
        new_b_path = Path(disable_mod_folder(str(mod_b_dir)))
        if not new_b_path.name.startswith("__DISABLED__"):
            raise SystemExit("Disable-by-rename failed")

        # Rebuild mod objects after rename, marking user_disabled like scan does
        mod_a2 = Mod(mod_a_dir.name, str(mod_a_dir))
        mod_b2 = Mod(new_b_path.name, str(new_b_path))
        mod_b2.user_disabled = True

        analyze_xml(mod_a2)
        analyze_xml(mod_b2)

        detect_conflicts([mod_a2, mod_b2])

        # Conflict detector should now skip user_disabled mods
        all_conflicts2 = (mod_a2.conflicts or []) + (mod_b2.conflicts or [])
        if any(c.get("conflict_type") == "duplicate_id" for c in all_conflicts2):
            raise SystemExit(f"Expected conflicts cleared after disable; still found: {all_conflicts2}")

        print("PASS")
        print("Mods root:", mods_root)
        print("Disabled folder:", new_b_path)


if __name__ == "__main__":
    main()
