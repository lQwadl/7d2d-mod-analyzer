from engines.conflict_engine import build_unified_conflicts
from mock_deploy.mutation import ConflictTrace, Mutation


class Mod:
    def __init__(self, name: str, load_order: int):
        self.name = name
        self.load_order = load_order
        self.user_disabled = False
        self.conflicts = []
        self.is_overhaul = False


class _State:
    def __init__(self):
        self.last_mut = {}


def test_sim_append_append_is_suppressed():
    a = Mod("010_A", 10)
    b = Mod("020_B", 20)

    first = Mutation(mod=a.name, file="items.xml", xpath="/x", op="append", value="A", order=1)
    second = Mutation(mod=b.name, file="items.xml", xpath="/x", op="append", value="B", order=2)
    ct = ConflictTrace(xpath=first.xpath, file=first.file, first=first, second=second, kind="append-append")

    unified = build_unified_conflicts(mods=[a, b], sim_state=_State(), sim_conflicts=[ct])
    assert not unified, unified


def test_sim_nonoverride_maps_to_load_order_priority_and_is_resolvable():
    a = Mod("010_A", 10)
    b = Mod("020_B", 20)

    first = Mutation(mod=a.name, file="items.xml", xpath="/x", op="remove", value="", order=1)
    second = Mutation(mod=b.name, file="items.xml", xpath="/x", op="set", value="B", order=2)
    ct = ConflictTrace(xpath=first.xpath, file=first.file, first=first, second=second, kind="remove-set")

    unified = build_unified_conflicts(mods=[a, b], sim_state=_State(), sim_conflicts=[ct])
    assert unified
    e = unified[0]
    assert e.get("source") == "sim"
    assert e.get("type") == "load_order_priority"
    assert bool(e.get("resolvable", False)) is True
