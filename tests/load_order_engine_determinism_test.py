from __future__ import annotations


def test_compute_load_order_is_deterministic_and_does_not_crash():
    from logic.load_order_engine import compute_load_order

    class Mod:
        def __init__(self, name: str):
            self.name = name
            self.path = ""  # avoid filesystem scanning
            self.disabled = False
            self.categories = []
            self.category = ""
            self.conflicts = []

    mods = [
        Mod("Zeta"),
        Mod("Alpha"),
        Mod("999_ConflictPatch_Test"),
        Mod("Beta"),
    ]

    ordered1, report1 = compute_load_order(mods)
    ordered2, report2 = compute_load_order(mods)

    assert [m.name for m in ordered1] == [m.name for m in ordered2]
    assert report1.errors == report2.errors
