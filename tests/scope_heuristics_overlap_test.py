from __future__ import annotations


def test_scope_heuristic_does_not_flag_without_evidence_overlap(tmp_path):
    from logic.scope_heuristics import filter_overlapping_mods

    class Mod:
        def __init__(self, name: str, *, semantic_edits=None, xml_files=None):
            self.name = name
            self.semantic_edits = semantic_edits if semantic_edits is not None else []
            self.xml_files = xml_files if xml_files is not None else set()

    # Simulate the user's example: both mention "stack" in name (scope),
    # but touch different semantic targets.
    quick_stack = Mod(
        "QuickStack",
        semantic_edits=[{"file": "xui/common.xml", "target": "xui:inventory"}],
        xml_files={"xui/common.xml"},
    )
    dew_stack = Mod(
        "IncreaseDewCollectorStackSize",
        semantic_edits=[{"file": "items.xml", "target": "item:dew/prop:Stacknumber"}],
        xml_files={"items.xml"},
    )

    overlapping, kind, samples = filter_overlapping_mods(quick_stack, [dew_stack])
    assert overlapping == []
    assert kind == "none"
    assert samples == []


def test_scope_heuristic_flags_with_semantic_overlap(tmp_path):
    from logic.scope_heuristics import filter_overlapping_mods

    class Mod:
        def __init__(self, name: str, *, semantic_edits=None, xml_files=None):
            self.name = name
            self.semantic_edits = semantic_edits if semantic_edits is not None else []
            self.xml_files = xml_files if xml_files is not None else set()

    a = Mod("A", semantic_edits=[{"file": "items.xml", "target": "item:foo/prop:Bar"}], xml_files={"items.xml"})
    b = Mod("B", semantic_edits=[{"file": "items.xml", "target": "item:foo/prop:Bar"}], xml_files={"items.xml"})

    overlapping, kind, samples = filter_overlapping_mods(a, [b])
    assert [m.name for m in overlapping] == ["B"]
    assert kind == "semantic"
    assert any("items.xml" in s for s in samples)
