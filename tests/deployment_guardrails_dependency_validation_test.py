from __future__ import annotations

from pathlib import Path

from tests._test_tmp import temp_dir


def _write_modinfo_dependency(mod_dir: Path, dep_name: str) -> None:
    # Keep structure minimal; guardrails parser accepts multiple tag spellings.
    xml = f"""<?xml version=\"1.0\" encoding=\"utf-8\"?>
<ModInfo>
  <Dependencies>
    <Dependency name=\"{dep_name}\" />
  </Dependencies>
</ModInfo>
"""
    (mod_dir / "ModInfo.xml").write_text(xml, encoding="utf-8")


def test_dependency_validation_matches_folder_names_not_display_names():
    from logic.deployment_guardrails import validate_dependencies_in_load_order

    with temp_dir("dep_guardrails_") as root:
        dep = root / "001_MyDep"
        dep.mkdir(parents=True, exist_ok=True)

        main = root / "010_MainMod"
        main.mkdir(parents=True, exist_ok=True)
        _write_modinfo_dependency(main, "MyDep")

        enabled_mods = [
            ("Awesome Dependency Display Name", str(dep)),
            ("Main Mod Display Name", str(main)),
        ]

        issues = validate_dependencies_in_load_order(enabled_mods=enabled_mods)
        assert issues == []


def test_dependency_validation_detects_load_order_violation():
    from logic.deployment_guardrails import validate_dependencies_in_load_order

    with temp_dir("dep_guardrails_") as root:
        dep = root / "001_MyDep"
        dep.mkdir(parents=True, exist_ok=True)

        main = root / "010_MainMod"
        main.mkdir(parents=True, exist_ok=True)
        _write_modinfo_dependency(main, "MyDep")

        # Wrong order: dependent before dependency.
        enabled_mods = [
            ("Main Mod", str(main)),
            ("Dependency", str(dep)),
        ]

        issues = validate_dependencies_in_load_order(enabled_mods=enabled_mods)
        reasons = {getattr(i, "reason", "") for i in issues}
        assert "dependency_load_order" in reasons


def test_dependency_validation_detects_missing_dependency():
    from logic.deployment_guardrails import validate_dependencies_in_load_order

    with temp_dir("dep_guardrails_") as root:
        main = root / "010_MainMod"
        main.mkdir(parents=True, exist_ok=True)
        _write_modinfo_dependency(main, "DoesNotExist")

        enabled_mods = [("Main Mod", str(main))]

        issues = validate_dependencies_in_load_order(enabled_mods=enabled_mods)
        reasons = {getattr(i, "reason", "") for i in issues}
        assert "missing_dependency" in reasons
