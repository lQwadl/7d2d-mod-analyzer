from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from logic.load_order_engine import compute_load_order


@dataclass
class _M:
    name: str
    path: str
    disabled: bool = False
    is_framework: bool = False


def _mk_mod_dir(tmp_path: Path, name: str, *, with_windows: bool = False) -> Path:
    d = tmp_path / name
    d.mkdir(parents=True, exist_ok=True)
    if with_windows:
        p = d / "Config" / "XUi_Menu" / "windows.xml"
        p.parent.mkdir(parents=True, exist_ok=True)
        # Root tag intentionally *not* <configs> to mimic full replacement UI frameworks.
        p.write_text("<windows></windows>", encoding="utf-8")
    return d


def test_compute_load_order_enforces_framework_mods_first(tmp_path: Path) -> None:
    sc = _mk_mod_dir(tmp_path, "SCore", with_windows=True)
    ui = _mk_mod_dir(tmp_path, "UIFramework", with_windows=True)
    xr = _mk_mod_dir(tmp_path, "XUiRCore", with_windows=True)
    other = _mk_mod_dir(tmp_path, "SomeOtherUIMod", with_windows=True)

    mods = [
        _M(name="SomeOtherUIMod", path=str(other), is_framework=False),
        _M(name="UIFramework", path=str(ui), is_framework=True),
        _M(name="XUiRCore", path=str(xr), is_framework=True),
        _M(name="SCore", path=str(sc), is_framework=True),
    ]

    ordered, _report = compute_load_order(mods, include_disabled=True)
    names = [m.name for m in ordered]

    assert names[:3] == ["SCore", "UIFramework", "XUiRCore"]
