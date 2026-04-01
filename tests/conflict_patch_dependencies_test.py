from __future__ import annotations


def test_generated_conflict_patch_declares_dependencies(tmp_path):
    from logic.conflict_patch import create_conflict_patch
    from logic.load_order_engine import parse_declared_dependencies

    class Side:
        def __init__(self, mod: str, value: str = ""):
            self.mod = mod
            self.value = value

    class Conflict:
        def __init__(self):
            self.kind = "override"
            self.file = "items.xml"
            self.xpath = "/items/item[@name='foo']/property[@name='Bar']"
            self.first = Side("001_ModA", "AAA")
            self.second = Side("002_ModB", "BBB")

    patch_dir = create_conflict_patch(str(tmp_path), [Conflict()], prefer="A", output_root=str(tmp_path))
    deps = parse_declared_dependencies(patch_dir)

    # normalize_mod_id should strip NNN_ prefixes
    assert "ModA" in deps
    assert "ModB" in deps
