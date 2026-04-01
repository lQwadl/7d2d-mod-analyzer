import os

from tests._test_tmp import temp_dir


def _mkfile(path: str, content: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


class DummyMod:
    def __init__(self, name: str, path: str, load_order: int):
        self.name = name
        self.path = path
        self.load_order = load_order
        self.enabled = True
        self.disabled = False
        self.user_disabled = False
        self.is_patch = False
        self.is_overhaul = False
        self.categories = []
        self.category = "Miscellaneous"

        self.xml_files = set()
        self.systems = set()
        self.xml_targets = {}
        self.semantic_edits = []
        self.conflicts = []


def test_xui_xml_overlap_is_load_order_priority():
    from logic.conflict_detector import detect_conflicts
    from scanner.xml_analyzer import analyze_xml

    with temp_dir("xui_conflict_") as root:
        mod_a_dir = os.path.join(str(root), "010_A")
        mod_b_dir = os.path.join(str(root), "020_B")

        # Two UI mods touching the same UI target in XUI_Common/styles.xml
        a_xml = """<?xml version='1.0'?>
<configs>
  <set xpath=\"//styles/style[@name='header']/@color\">#fff</set>
</configs>
"""
        b_xml = """<?xml version='1.0'?>
<configs>
  <set xpath=\"//styles/style[@name='header']/@color\">#000</set>
</configs>
"""

        _mkfile(os.path.join(mod_a_dir, "XUI_Common", "styles.xml"), a_xml)
        _mkfile(os.path.join(mod_b_dir, "XUI_Common", "styles.xml"), b_xml)

        mod_a = DummyMod("010_A", mod_a_dir, load_order=10)
        mod_b = DummyMod("020_B", mod_b_dir, load_order=20)

        analyze_xml(mod_a)
        analyze_xml(mod_b)

        detect_conflicts([mod_a, mod_b])

        def _find_ui_conflict(mod):
            return [
                c
                for c in mod.conflicts
                if c.get("file") == "xui_common/styles.xml" and c.get("conflict_type") == "load_order_priority"
            ]

        a_conf = _find_ui_conflict(mod_a)
        b_conf = _find_ui_conflict(mod_b)

        assert a_conf, "Expected UI XUi conflict on mod_a"
        assert b_conf, "Expected UI XUi conflict on mod_b"
        assert a_conf[0]["level"] in ("warn", "error")
        assert b_conf[0]["level"] in ("warn", "error")

        # Deterministic load-order recommendation should be present.
        for c in (a_conf[0], b_conf[0]):
            assert c.get("recommended_front") in ("010_A", "020_B")
            assert c.get("recommended_back") in ("010_A", "020_B")
            assert c.get("recommended_front") != c.get("recommended_back")
            assert isinstance(c.get("recommended_reason"), str)
