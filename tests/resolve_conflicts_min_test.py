"""Minimal acceptance test for Resolve Conflicts patch generation.

This is a script-style test (no pytest dependency) that verifies:
- Patch folder exists
- ModInfo.xml exists
- Patch loads last by name prefix
- Simulation conflicts on a key are considered resolved (last writer is patch)

Run:
  python tests/resolve_conflicts_min_test.py
"""

import os
from pathlib import Path

import sys

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mock_deploy.engine import simulate_deployment
from logic.conflict_patch import create_conflict_patch, PATCH_PREFIX
from tests._test_tmp import temp_dir


def _write_mod(mod_dir: Path, xml_name: str, body: str) -> None:
    (mod_dir / "Config").mkdir(parents=True, exist_ok=True)
    (mod_dir / "ModInfo.xml").write_text(
        """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<xml><ModInfo><Name value=\"X\"/></ModInfo></xml>
""",
        encoding="utf-8",
    )
    (mod_dir / "Config" / xml_name).write_text(body, encoding="utf-8")


def main():
    with temp_dir("resolve_conflicts_") as tmp_root:
        mods_root = tmp_root / "Mods"
        mods_root.mkdir(parents=True, exist_ok=True)

        mod_a = mods_root / "001_ModA"
        mod_b = mods_root / "002_ModB"

        # Two mods that set the same xpath to different values
        _write_mod(
            mod_a,
            "items.xml",
            """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<configs>
  <set xpath=\"/configs/item[@name='x']\">A</set>
</configs>
""",
        )
        _write_mod(
            mod_b,
            "items.xml",
            """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<configs>
  <set xpath=\"/configs/item[@name='x']\">B</set>
</configs>
""",
        )

        state1, conf1 = simulate_deployment([(mod_a.name, str(mod_a)), (mod_b.name, str(mod_b))])
        if not conf1:
            raise SystemExit("Expected conflicts before patch, found none")

        # Generate patch preferring A
        patch_dir = create_conflict_patch(str(mods_root), conf1[:1], prefer="A")

        # File system checks
        assert patch_dir.exists(), "Patch folder missing"
        assert (patch_dir / "ModInfo.xml").exists(), "ModInfo.xml missing"
        assert patch_dir.name.startswith(PATCH_PREFIX), "Patch naming/prefix wrong"

        # Patch loads last (lexical)
        names = sorted([p.name for p in mods_root.iterdir() if p.is_dir()], key=lambda s: s.lower())
        assert names[-1].startswith(PATCH_PREFIX), "Patch does not sort last"

        # Re-simulate with patch last
        state2, _conf2 = simulate_deployment(
            [
                (mod_a.name, str(mod_a)),
                (mod_b.name, str(mod_b)),
                (patch_dir.name, str(patch_dir)),
            ]
        )

        # Consider resolved when last writer is the patch mod
        key = ("items.xml", "/configs/item[@name='x']")
        last = state2.last_mut.get(key)
        assert last and last.mod == patch_dir.name, "Patch did not become last writer"

        print("PASS")
        print("Patch:", patch_dir)


if __name__ == "__main__":
    main()
