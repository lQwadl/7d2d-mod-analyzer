"""Script-style tests for engine evidence hashing.

Run:
  python tests/engine_evidence_hash_test.py
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engines.evidence import conflict_evidence_hash


def main():
    h1 = conflict_evidence_hash(
        source="scan",
        conflict_type="duplicate_id",
        file="items.xml",
        target="/items/item[@name='x']",
        mod_a="010_ModA",
        mod_b="020_ModB",
        kind="error",
    )
    h2 = conflict_evidence_hash(
        source="scan",
        conflict_type="duplicate_id",
        file="items.xml",
        target="/items/item[@name='x']",
        mod_a="ModB",
        mod_b="__DISABLED__010_ModA",
        kind="error",
    )
    assert h1 == h2, "hash should be order-independent and normalize mod ids"

    h3 = conflict_evidence_hash(
        source="scan",
        conflict_type="duplicate_id",
        file="items.xml",
        target="/items/item[@name='x']",
        mod_a="010_ModA",
        mod_b="020_ModB",
        kind="warn",
    )
    assert h1 != h3, "hash should differ when kind differs"

    print("PASS")


if __name__ == "__main__":
    main()
