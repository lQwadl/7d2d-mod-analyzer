import os
import sys
from tests._test_tmp import _tmp_root
import tkinter as tk
from tkinter import filedialog

# Ensure project root is on sys.path so package imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gui.app import ModAnalyzerApp

# Hide GUI window
root = tk.Tk()
root.withdraw()
app = ModAnalyzerApp(root)

# Run analysis (this populates mods and recommended_order)
app.analyze()

# Ensure recommended_order exists
if not getattr(app, "recommended_order", None):
    app.recommended_order = app.mods[:]

# Prepare temp files
tmpdir = str(_tmp_root())
txt_path = os.path.join(tmpdir, "recommended_load_order_test.txt")
json_path = os.path.join(tmpdir, "recommended_load_order_test.json")

# Monkeypatch filedialog to return txt path first, then json path
orig_asksave = filedialog.asksaveasfilename

try:
    # Export TXT
    filedialog.asksaveasfilename = lambda **kwargs: txt_path
    app.generate_load_order()

    # Export JSON
    filedialog.asksaveasfilename = lambda **kwargs: json_path
    app.generate_load_order()
finally:
    filedialog.asksaveasfilename = orig_asksave

# Read GUI output
gui_text = app.output.get("1.0", "end").strip()

# Read exported files
txt_contents = ""
json_contents = ""
if os.path.exists(txt_path):
    with open(txt_path, "r", encoding="utf-8") as f:
        txt_contents = f.read()
if os.path.exists(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        json_contents = f.read()

# Basic verifications
results = []
if "RECOMMENDED LOAD ORDER" in gui_text or "RECOMMENDED LOAD ORDER" in gui_text.upper():
    results.append("GUI: recommended header present")
else:
    results.append("GUI: recommended header MISSING")

if app.recommended_order and len(app.recommended_order) == len(set(m.name for m in app.recommended_order)):
    results.append("State: recommended_order has no duplicate names")
else:
    results.append("State: duplicates found in recommended_order")

if txt_contents:
    results.append(f"TXT Export: written ({len(txt_contents.splitlines())} lines)")
else:
    results.append("TXT Export: MISSING")

if json_contents:
    results.append(f"JSON Export: written ({len(json_contents.splitlines())} lines)")
else:
    results.append("JSON Export: MISSING")

# Print concise report
print("\n".join(results))
print("\nSample GUI output (first 20 lines):")
for i, line in enumerate(gui_text.splitlines()[:20], 1):
    print(f"{i:02d}: {line}")

print("\nTXT sample (first 10 lines):")
for i, line in enumerate(txt_contents.splitlines()[:10], 1):
    print(f"{i:02d}: {line}")

print("\nJSON sample (first 10 lines):")
for i, line in enumerate(json_contents.splitlines()[:10], 1):
    print(f"{i:02d}: {line}")

print("\nTest files:")
print(txt_path)
print(json_path)
