from __future__ import annotations

from pathlib import Path

import pytest

from logic.deployment_guardrails import validate_mod_xml_safety


def _write(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def test_validate_mod_xml_safety_allows_configs_root(tmp_path: Path) -> None:
    mod_dir = tmp_path / "MySafeMod"
    xml_path = mod_dir / "Config" / "XUi_Common" / "styles.xml"
    _write(xml_path, "<configs></configs>")

    # Should not raise.
    validate_mod_xml_safety(mod_dir)


def test_validate_mod_xml_safety_blocks_full_replacement_root(tmp_path: Path) -> None:
    mod_dir = tmp_path / "MyBadMod"
    xml_path = mod_dir / "Config" / "XUi_Common" / "styles.xml"
    _write(xml_path, "<styles></styles>")

    with pytest.raises(RuntimeError) as exc:
        validate_mod_xml_safety(mod_dir)

    msg = str(exc.value)
    assert "BLOCKED MOD DEPLOYMENT" in msg
    assert "Mod: MyBadMod" in msg
    assert "Reason: Full XML replacement of critical UI file." in msg
    assert str(xml_path) in msg


def test_validate_mod_xml_safety_allows_framework_full_replacement(tmp_path: Path) -> None:
    mod_dir = tmp_path / "Better UI"
    xml_path = mod_dir / "Config" / "XUi_Common" / "styles.xml"
    _write(xml_path, "<styles></styles>")

    # Mark as framework via metadata store, not folder name.
    meta_path = tmp_path / "mod_metadata.json"
    meta_path.write_text(
        "{\n"
        '  "version": 1,\n'
        '  "mods": {\n'
        '    "Better UI": {\n'
        '      "mod_id": "Better UI",\n'
        '      "signature": "",\n'
        '      "categories": [],\n'
        '      "primary_category": "Miscellaneous",\n'
        '      "evidence": {},\n'
        '      "last_scanned": "",\n'
        '      "isFramework": true\n'
        "    }\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )

    import os

    os.environ["MOD_ANALYZER_METADATA_PATH"] = str(meta_path)
    try:
        validate_mod_xml_safety(mod_dir)
    finally:
        os.environ.pop("MOD_ANALYZER_METADATA_PATH", None)


def test_validate_mod_xml_safety_blocks_malformed_xml(tmp_path: Path) -> None:
    mod_dir = tmp_path / "MyMalformedMod"
    xml_path = mod_dir / "Config" / "XUi_Menu" / "windows.xml"
    _write(xml_path, "<configs")

    with pytest.raises(RuntimeError):
        validate_mod_xml_safety(mod_dir)


def test_validate_mod_xml_safety_ignores_xml_outside_config(tmp_path: Path) -> None:
    mod_dir = tmp_path / "MyNonConfigMod"
    xml_path = mod_dir / "styles.xml"
    _write(xml_path, "<styles></styles>")

    # styles.xml is critical, but not under Config/, so should not block.
    validate_mod_xml_safety(mod_dir)


def test_validate_mod_xml_safety_config_detection_is_case_insensitive(tmp_path: Path) -> None:
    mod_dir = tmp_path / "MyCaseMod"
    xml_path = mod_dir / "cOnFiG" / "XUi_Common" / "controls.xml"
    _write(xml_path, "<controls></controls>")

    with pytest.raises(RuntimeError):
        validate_mod_xml_safety(mod_dir)
