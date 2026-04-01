from __future__ import annotations


def test_stabilizing_patch_emits_remove_for_final_remove(tmp_path):
    from mock_deploy.engine import simulate_deployment
    from logic.conflict_patch import create_stabilizing_patch, PATCH_PREFIX

    def _write_mod(mod_dir, xml_name: str, body: str) -> None:
        (mod_dir / "Config").mkdir(parents=True, exist_ok=True)
        (mod_dir / "ModInfo.xml").write_text(
            """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<xml><ModInfo><Name value=\"X\"/></ModInfo></xml>
""",
            encoding="utf-8",
        )
        (mod_dir / "Config" / xml_name).write_text(body, encoding="utf-8")

    mods_root = tmp_path / "Mods"
    mods_root.mkdir(parents=True, exist_ok=True)

    mod_a = mods_root / "001_ModA"
    mod_b = mods_root / "002_ModB"

    # A sets, then B removes: final op is remove.
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
  <remove xpath=\"/configs/item[@name='x']\" />
</configs>
""",
    )

    state1, conf1 = simulate_deployment([(mod_a.name, str(mod_a)), (mod_b.name, str(mod_b))])
    assert conf1, "Expected at least one simulator conflict"

    non_override = [c for c in conf1 if getattr(c, "kind", None) != "override"]
    assert non_override, "Expected at least one non-override conflict"

    patch_dir = create_stabilizing_patch(
        str(mods_root), state=state1, conflicts=non_override, output_root=str(mods_root)
    )

    assert patch_dir.exists()
    assert patch_dir.name.startswith(PATCH_PREFIX)
    assert (patch_dir / "ModInfo.xml").exists()

    patch_xml = (patch_dir / "Config" / "items.xml").read_text(encoding="utf-8")
    assert "<remove" in patch_xml
    assert "/configs/item[@name='x']" in patch_xml

    state2, _conf2 = simulate_deployment(
        [(mod_a.name, str(mod_a)), (mod_b.name, str(mod_b)), (patch_dir.name, str(patch_dir))]
    )

    key = ("items.xml", "/configs/item[@name='x']")
    last = state2.last_mut.get(key)
    assert last and last.mod == patch_dir.name, "Stabilizing patch did not become last writer"
