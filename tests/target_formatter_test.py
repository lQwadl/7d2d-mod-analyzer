"""Script-style test for human-friendly conflict target formatting.

Run:
  python tests/target_formatter_test.py
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from logic.target_formatter import format_target_display, xpath_to_target


def main():
    xp = "//items/item[@name='gunAK47']/property[@name='Quality']"
    t = xpath_to_target(xp)
    assert t == "item:gunAK47/property:Quality", t

    disp = format_target_display(file="items.xml", target=t)
    assert "gunAK47" in disp and "Quality" in disp, disp

    disp2 = format_target_display(file="items.xml", target=xp)
    assert "gunAK47" in disp2 and "Quality" in disp2, disp2

    ad = format_target_display(file="assets", target="asset:textures/weapons/pipePistol.dds")
    assert ad.lower().startswith("texture:"), ad
    assert "pipepistol.dds" in ad.lower(), ad

    print("PASS")


if __name__ == "__main__":
    main()
