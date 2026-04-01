"""Script-style tests for ModStateStore (mods_state.json persistence).

Run:
  python tests/mod_state_store_test.py
"""

import os

# Ensure project root is importable when running as a script
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from logic.mod_state_store import ModStateStore
from tests._test_tmp import temp_dir


def main():
    with temp_dir("mod_state_") as root:
        path = os.path.join(str(root), "mods_state.json")

        store = ModStateStore(path)
        store.load()  # should be a no-op when file doesn't exist

        store.set("mymod", enabled=True, user_disabled=False)
        store.set("othermod", enabled=False, user_disabled=True)
        store.save()

        store2 = ModStateStore(path)
        store2.load()

        st1 = store2.get("mymod")
        assert st1 is not None
        assert st1.enabled is True
        assert st1.user_disabled is False

        st2 = store2.get("othermod")
        assert st2 is not None
        assert st2.enabled is False
        assert st2.user_disabled is True

        # Invariant: user_disabled implies enabled False (even if persisted otherwise)
        with open(path, "w", encoding="utf-8") as f:
            f.write('{"badmod": {"enabled": true, "user_disabled": true}}')

        store3 = ModStateStore(path)
        store3.load()
        st3 = store3.get("badmod")
        assert st3 is not None
        assert st3.user_disabled is True
        assert st3.enabled is False

    print("PASS")


if __name__ == "__main__":
    main()
