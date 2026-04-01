"""Script-style test for safe, file-driven CopyDeployer.

Run:
  python tests/deployment_copy_deployer_file_driven_test.py

Verifies:
- Per-file copy logging is emitted before each copy
- Files drive directory creation (no empty mod folder creation)
- Empty source mod folder is treated as fatal (raises)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from deployment.copy_deployer import CopyDeployer
from deployment.errors import DeploymentError
from tests._test_tmp import temp_dir


def _write_file(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def main() -> None:
    with temp_dir("deploy_") as tmp_root:
        src_root = tmp_root / "Source"
        tgt_root = tmp_root / "SteamMods"
        manifests_dir = tmp_root / "manifests"

        # Build a source mod with nested files + an empty directory.
        mod_a = src_root / "ModA"
        (mod_a / "EmptyDir").mkdir(parents=True, exist_ok=True)
        _write_file(mod_a / "ModInfo.xml", b"<xml/>\n")
        _write_file(mod_a / "Config" / "items.xml", b"<configs/>\n")

        logs: list[str] = []

    def log(msg: str) -> None:
        logs.append(msg)

        d = CopyDeployer(manifests_dir=str(manifests_dir))
        d.deploy(source_mod_dirs=[("001_ModA", str(mod_a))], target_path=str(tgt_root), log=log)

    # Must have at least one COPY FILE log entry.
        copy_logs = [m for m in logs if m.startswith("COPY FILE:")]
        assert copy_logs, "Expected per-file COPY FILE logs"

    # Destination must contain files and sizes must match.
        dest_mod = tgt_root / "001_ModA"
        assert dest_mod.exists() and dest_mod.is_dir(), "Destination mod folder missing"

        src_files = sorted([p for p in mod_a.rglob("*") if p.is_file()])
        for sf in src_files:
            rel = sf.relative_to(mod_a)
            df = dest_mod / rel
            assert df.exists() and df.is_file(), f"Missing deployed file: {df}"
            assert sf.stat().st_size == df.stat().st_size, f"Size mismatch: {sf} -> {df}"

    # Empty source mod should be fatal and must not create an empty mod folder.
        mod_empty = src_root / "EmptyMod"
        mod_empty.mkdir(parents=True, exist_ok=True)

        logs.clear()
        try:
            d.deploy(source_mod_dirs=[("002_Empty", str(mod_empty))], target_path=str(tgt_root), log=log)
            raise SystemExit("Expected DeploymentError for empty source mod")
        except DeploymentError:
            pass

        assert not (tgt_root / "002_Empty").exists(), "Empty mod folder should not be created"

        print("PASS")
        print("Target:", tgt_root)


if __name__ == "__main__":
    main()
