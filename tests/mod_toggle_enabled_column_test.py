import os
import sys

import pytest

tk = pytest.importorskip("tkinter")

# Ensure project root is on sys.path so package imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gui.app import Mod, ModAnalyzerApp


def test_mod_lookup_initialized_and_populated_on_refresh_table():
    try:
        root = tk.Tk()
    except Exception as e:
        # tkinter can be importable while Tcl/Tk runtime isn't properly installed.
        pytest.skip(f"Tkinter not usable in this environment: {e}")
    root.withdraw()
    app = ModAnalyzerApp(root)

    # Build a minimal mod list; refresh_table groups by category and inserts rows.
    m1 = Mod(name="TestModA", path="iid_test_mod_a")
    m1.category = "Miscellaneous"

    app.mods = [m1]
    app.refresh_table()

    # The click-to-toggle path depends on this lookup.
    assert hasattr(app, "mod_lookup")
    assert isinstance(app.mod_lookup, dict)
    assert "iid_test_mod_a" in app.mod_lookup
    assert app.mod_lookup["iid_test_mod_a"] is m1

    try:
        root.destroy()
    except Exception:
        pass
