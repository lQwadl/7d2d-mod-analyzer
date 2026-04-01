from logic.resolution_policy import WinnerDecision, decide_winner


class Mod:
    def __init__(
        self, name: str, *, tier: str = "", category: str = "", is_overhaul: bool = False, load_order: int = 0
    ):
        self.name = name
        self.tier = tier
        self.category = category
        self.categories = [category] if category else []
        self.is_overhaul = is_overhaul
        self.load_order = load_order
        self.path = ""  # not used by these tests


def test_overhaul_wins_loads_later():
    a = Mod("A", is_overhaul=False, load_order=10)
    b = Mod("B", is_overhaul=True, load_order=20)

    d = decide_winner([a, b], mod_a_name=a.name, mod_b_name=b.name, conflict_type="load_order_priority")
    assert isinstance(d, WinnerDecision)
    assert d.back == b.name


def test_patch_mod_tier_wins():
    a = Mod("A", tier="Content Additions", load_order=10)
    b = Mod("B", tier="Patch Mods", load_order=20)

    d = decide_winner([a, b], mod_a_name=a.name, mod_b_name=b.name, conflict_type="load_order_priority")
    assert d.back == b.name


def test_dependency_forces_ordering():
    # If A depends on B, then B must load before A.
    a = Mod("A", tier="Content Additions", load_order=20)
    b = Mod("B", tier="Core Frameworks", load_order=10)

    deps = {"A": {"B"}, "B": set()}
    d = decide_winner([a, b], mod_a_name=a.name, mod_b_name=b.name, conflict_type="load_order_priority", deps=deps)
    assert d.front == b.name
    assert d.back == a.name
