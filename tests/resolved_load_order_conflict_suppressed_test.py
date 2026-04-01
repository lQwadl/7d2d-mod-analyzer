import os


def test_resolved_load_order_priority_is_suppressed():
    """If order already satisfies recommendation, conflict should not reappear."""

    from engines.conflict_engine import build_unified_conflicts

    class Mod:
        def __init__(self, name: str, load_order: int):
            self.name = name
            self.load_order = load_order
            self.user_disabled = False
            self.conflicts = []
            self.is_overhaul = False

    a = Mod("010_A", 10)
    b = Mod("020_B", 20)

    # A loads earlier, B later. Recommended order matches current state.
    a.conflicts.append(
        {
            "level": "warn",
            "file": "xui_common/styles.xml",
            "target": "//styles/style[@name='header']/@color",
            "with": b.name,
            "reason": "UI order-sensitive",
            "suggestion": "swap order",
            "conflict_type": "load_order_priority",
            "recommended_front": a.name,
            "recommended_back": b.name,
            "recommended_reason": "B should win",
        }
    )

    unified = build_unified_conflicts(mods=[a, b], sim_state=None, sim_conflicts=None)

    # Should be suppressed because load order already satisfies recommendation.
    assert not [e for e in unified if e.get("type") == "load_order_priority"], unified


def test_unresolved_load_order_priority_is_emitted():
    from engines.conflict_engine import build_unified_conflicts

    class Mod:
        def __init__(self, name: str, load_order: int):
            self.name = name
            self.load_order = load_order
            self.user_disabled = False
            self.conflicts = []
            self.is_overhaul = False

    a = Mod("010_A", 30)
    b = Mod("020_B", 20)

    # Recommendation: B should load later, but A currently loads later.
    a.conflicts.append(
        {
            "level": "warn",
            "file": "xui_common/styles.xml",
            "target": "//styles/style[@name='header']/@color",
            "with": b.name,
            "reason": "UI order-sensitive",
            "suggestion": "swap order",
            "conflict_type": "load_order_priority",
            "recommended_front": a.name,
            "recommended_back": b.name,
            "recommended_reason": "B should win",
        }
    )

    unified = build_unified_conflicts(mods=[a, b], sim_state=None, sim_conflicts=None)
    assert [e for e in unified if e.get("type") == "load_order_priority"], unified
