import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tests._test_tmp import temp_dir
from logic.resolution_knowledge import ResolutionKnowledgeBase


def main():
    with temp_dir("resolution_kb_") as root:
        path = os.path.join(str(root), "resolution_knowledge.json")
        kb = ResolutionKnowledgeBase(path)

        # unknown type: should create entry
        assert kb.list_options("unknown") == []

        # add attempts: uncommon promotion
        for _ in range(3):
            kb.record_attempt(conflict_type="xml_override", resolution_id="merge", success=True)
        kb.save()

        kb2 = ResolutionKnowledgeBase(path)
        opts = kb2.list_options("xml_override")
        # merge should now be common
        assert any(o.resolution_id == "merge" and o.tier == "common" for o in opts)

        # demote/risky marking
        for _ in range(3):
            kb2.record_attempt(conflict_type="duplicate_id", resolution_id="disable", success=False)
        opts2 = kb2.list_options("duplicate_id")
        disable = next(o for o in opts2 if o.resolution_id == "disable")
        assert disable.risky is True

        # --- de-dup/compact: same id appears in both tiers -> merge into one ---
        kb2.data.setdefault("conflict_types", {})
        kb2.data["conflict_types"]["duplicate_id"] = {
            "common_resolutions": [
                {
                    "id": "disable",
                    "label": "Disable one mod",
                    "applied_count": 1,
                    "success_count": 1,
                    "risky": False,
                },
            ],
            "uncommon_resolutions": [
                {
                    "id": "disable",
                    "label": "Disable one mod (duplicate)",
                    "applied_count": 2,
                    "success_count": 0,
                    "risky": True,
                },
            ],
            "last_used": None,
        }
        kb2.save()
        kb3 = ResolutionKnowledgeBase(path)
        opts3 = kb3.list_options("duplicate_id", include_disabled=True)
        disables = [o for o in opts3 if o.resolution_id == "disable"]
        assert len(disables) == 1
        # merged counts
        assert disables[0].applied_count >= 3

        # --- auto-disable: consistently failing strategy becomes hidden ---
        for _ in range(8):
            kb3.record_attempt(conflict_type="xml_override", resolution_id="always_fail", success=False)
        kb3.save()
        kb4 = ResolutionKnowledgeBase(path)
        # always_fail should now be disabled/hidden by default
        opts4 = kb4.list_options("xml_override")
        assert all(o.resolution_id != "always_fail" for o in opts4)
        # but visible if explicitly requested
        opts4_all = kb4.list_options("xml_override", include_disabled=True)
        assert any(o.resolution_id == "always_fail" and o.disabled is True for o in opts4_all)

    print("PASS")


if __name__ == "__main__":
    main()
