import os
from tests._test_tmp import _tmp_root


def test_export_loadorder_txt_preserves_input_order():
    # Import inside test so pytest collection doesn't eagerly initialize tkinter.
    from gui.app import ModAnalyzerApp

    class Mod:
        def __init__(self, name: str, path: str, tier: str, category: str):
            self.name = name
            self.path = path
            self.tier = tier
            self.category = category
            self.enabled = True
            self.user_disabled = False
            self.disabled = False

    # Intentionally provide a non-alphabetical order.
    mods = [
        Mod("ZZZ Second", r"C:\Mods\200_ZZZ_Second", "Overhauls", "Gameplay"),
        Mod("AAA First", r"C:\Mods\100_AAA_First", "Overhauls", "Gameplay"),
    ]

    app = ModAnalyzerApp.__new__(ModAnalyzerApp)  # bypass full GUI init

    out_path = os.path.join(str(_tmp_root()), "load_order_export_order_test.txt")
    try:
        app.export_loadorder_txt(out_path, mods)
        with open(out_path, "r", encoding="utf-8") as f:
            txt = f.read()

        second_idx = txt.find("200_ZZZ_Second")
        first_idx = txt.find("100_AAA_First")

        assert second_idx != -1, "Expected second mod to be present in export"
        assert first_idx != -1, "Expected first mod to be present in export"
        assert second_idx < first_idx, "Export must preserve computed/mod list order"
    finally:
        try:
            os.remove(out_path)
        except OSError:
            pass


def test_infer_tier_handles_missing_path_fast():
    from logic.load_order_engine import infer_tier, TIER_ORDER

    class Mod:
        name = "Some Mod"
        path = ""  # critical: used to scan '.' previously
        category = ""
        categories = []
        is_overhaul = False
        is_patch = False

    tier = infer_tier(Mod())
    assert tier in set(TIER_ORDER)
