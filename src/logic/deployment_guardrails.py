from __future__ import annotations

import os
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from logic.mod_metadata_store import normalize_mod_id


# ---------------------------------------------------------
# Guardrails / validation types
# ---------------------------------------------------------


@dataclass(frozen=True)
class ValidationIssue:
    level: str  # "ERROR" | "WARN" | "INFO"
    reason: str
    mod: str = ""
    file: str = ""
    details: str = ""


@dataclass(frozen=True)
class ModsDirStatus:
    game_mods_dir: str
    documents_mods_dir: str
    game_has_mods: bool
    documents_has_mods: bool


@dataclass(frozen=True)
class PreflightReport:
    ok: bool
    issues: List[ValidationIssue]
    mods_dir_status: Optional[ModsDirStatus] = None

    @property
    def errors(self) -> List[ValidationIssue]:
        return [i for i in (self.issues or []) if (i.level or "").upper() == "ERROR"]

    @property
    def warnings(self) -> List[ValidationIssue]:
        return [i for i in (self.issues or []) if (i.level or "").upper() == "WARN"]


# ---------------------------------------------------------
# Paths: single Mods directory enforcement
# ---------------------------------------------------------


def _safe_str(p: Any) -> str:
    try:
        return str(p or "")
    except Exception:
        return ""


def _default_documents_mods_dir() -> str:
    # Requirement explicitly wants Documents/7DaysToDie/Mods.
    try:
        return str(Path.home() / "Documents" / "7DaysToDie" / "Mods")
    except Exception:
        # Last resort: USERPROFILE
        up = os.getenv("USERPROFILE") or ""
        return str(Path(up) / "Documents" / "7DaysToDie" / "Mods")


def detect_mods_dirs(*, mods_root: str, documents_mods_dir: Optional[str] = None) -> ModsDirStatus:
    game_mods_dir = str(Path(mods_root))
    docs_dir = str(Path(documents_mods_dir) if documents_mods_dir else Path(_default_documents_mods_dir()))
    return ModsDirStatus(
        game_mods_dir=game_mods_dir,
        documents_mods_dir=docs_dir,
        game_has_mods=mods_present(game_mods_dir),
        documents_has_mods=mods_present(docs_dir),
    )


def mods_present(path: str) -> bool:
    """Return True if `path` looks like it contains mods.

    We consider a folder to "contain mods" if it contains at least one subdirectory
    that contains a ModInfo.xml OR any file at all under it.
    """
    try:
        p = Path(path)
        if not p.exists() or not p.is_dir():
            return False

        # Any ModInfo.xml under immediate children is a strong signal.
        try:
            for child in p.iterdir():
                if not child.is_dir():
                    continue
                # Ignore common non-mod folders.
                nm = (child.name or "").strip().lower()
                if not nm or nm in {".git", "__pycache__"}:
                    continue
                if (child / "ModInfo.xml").is_file():
                    return True
        except Exception:
            pass

        # Fallback: any file anywhere.
        for fp in p.rglob("*"):
            if fp.is_file():
                return True
        return False
    except Exception:
        return False


def validate_single_mods_dir(
    *, mods_root: str, documents_mods_dir: Optional[str] = None
) -> Tuple[ModsDirStatus, List[ValidationIssue]]:
    st = detect_mods_dirs(mods_root=mods_root, documents_mods_dir=documents_mods_dir)
    issues: List[ValidationIssue] = []

    if st.game_has_mods and st.documents_has_mods:
        issues.append(
            ValidationIssue(
                level="ERROR",
                reason="multiple_mods_dirs",
                details=(
                    "More than one Mods directory contains mods. 7DTD will load from both in unpredictable ways.\n\n"
                    f"- Game Mods: {st.game_mods_dir}\n"
                    f"- Documents Mods: {st.documents_mods_dir}\n\n"
                    "Fix: move/disable mods so only ONE of these folders contains mods."
                ),
            )
        )

    return st, issues


# ---------------------------------------------------------
# XML integrity checks
# ---------------------------------------------------------


def _iter_xml_files(root: Path) -> Iterable[Path]:
    # "Deployed XML" includes any *.xml anywhere inside the mod folder.
    # (Some mods keep XML outside Config.)
    try:
        yield from root.rglob("*.xml")
    except Exception:
        return


def _xml_is_patch_style(xml_path: Path) -> bool:
    """Heuristic: returns True if the XML looks like a patch (xpath ops)."""
    try:
        tree = ET.parse(str(xml_path))
        root = tree.getroot()
    except Exception:
        return False

    for elem in root.iter():
        try:
            if elem is root:
                continue
            if (elem.attrib or {}).get("xpath"):
                return True
        except Exception:
            continue
    return False


def validate_xml_file(*, mod_name: str, xml_path: Path) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []

    try:
        if not xml_path.exists() or not xml_path.is_file():
            issues.append(
                ValidationIssue(
                    level="ERROR",
                    reason="missing_xml",
                    mod=mod_name,
                    file=str(xml_path),
                    details="XML file missing",
                )
            )
            return issues

        try:
            size = xml_path.stat().st_size
        except Exception:
            size = -1

        if size <= 0:
            issues.append(
                ValidationIssue(
                    level="ERROR",
                    reason="empty_xml",
                    mod=mod_name,
                    file=str(xml_path),
                    details="XML file is empty (0 bytes)",
                )
            )
            return issues

        try:
            ET.parse(str(xml_path))
        except Exception as e:
            issues.append(
                ValidationIssue(
                    level="ERROR",
                    reason="invalid_xml",
                    mod=mod_name,
                    file=str(xml_path),
                    details=f"XML parse failed: {e}",
                )
            )

        return issues
    except Exception as e:
        issues.append(
            ValidationIssue(
                level="ERROR",
                reason="xml_validation_crash",
                mod=mod_name,
                file=str(xml_path),
                details=str(e),
            )
        )
        return issues


def validate_mod_xml_tree(*, mod_name: str, mod_path: str) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []
    root = Path(mod_path)
    if not root.exists() or not root.is_dir():
        return [
            ValidationIssue(
                level="ERROR",
                reason="missing_mod_folder",
                mod=mod_name,
                file=str(root),
                details="Mod folder missing",
            )
        ]

    for xml_path in _iter_xml_files(root):
        issues.extend(validate_xml_file(mod_name=mod_name, xml_path=xml_path))

    return issues


# ---------------------------------------------------------
# HARD STOP: Critical UI XML full replacements
# ---------------------------------------------------------


CRITICAL_UI_FILES = {
    "loadingscreen.xml",
    "styles.xml",
    "windows.xml",
    "controls.xml",
}


FRAMEWORK_MOD_KEYS = {
    "scor",
    "uiframework",
    "xuircore",
}


def _boolish(v: Any) -> bool:
    try:
        if isinstance(v, bool):
            return v
        if isinstance(v, (int, float)):
            return bool(v)
        s = str(v or "").strip().lower()
        return s in {"1", "true", "yes", "y", "on"}
    except Exception:
        return False


def _metadata_store_path() -> Path:
    """Path to the manager's persistent mod metadata store.

    Can be overridden for tests via MOD_ANALYZER_METADATA_PATH.
    """

    env = (os.getenv("MOD_ANALYZER_METADATA_PATH") or "").strip()
    if env:
        return Path(env)
    try:
        repo_root = Path(__file__).resolve().parents[1]
    except Exception:
        repo_root = Path(".")
    return repo_root / "data" / "mod_metadata.json"


def _framework_flag_from_metadata(mod_name: str) -> Optional[bool]:
    """Return framework flag from metadata store if present, else None."""

    try:
        mod_id = normalize_mod_id(mod_name)
        mp = _metadata_store_path()
        if not mp.exists() or not mp.is_file():
            return None
        try:
            import json

            data = json.loads(mp.read_text(encoding="utf-8")) or {}
        except Exception:
            return None
        mods = data.get("mods")
        if not isinstance(mods, dict):
            return None
        rec = mods.get(mod_id)
        if not isinstance(rec, dict):
            return None
        if "is_framework" in rec:
            return _boolish(rec.get("is_framework"))
        if "isFramework" in rec:
            return _boolish(rec.get("isFramework"))
        return None
    except Exception:
        return None


def is_framework_mod(mod_name: str) -> bool:
    """True if mod should be treated as a framework/base mod.

    Primary source: persistent metadata store flag (is_framework/isFramework).
    Fallback: name-key matching for compatibility.
    """

    flagged = _framework_flag_from_metadata(mod_name)
    if isinstance(flagged, bool):
        return flagged
    try:
        name = (mod_name or "").lower()
        return any(key in name for key in FRAMEWORK_MOD_KEYS)
    except Exception:
        return False


def _local_xml_tag(tag: str) -> str:
    """Return the local (non-namespaced) tag name, lowercased."""
    try:
        t = (tag or "").strip()
        if "}" in t:
            t = t.rsplit("}", 1)[-1]
        return t.lower()
    except Exception:
        return ""


def is_full_xml_replacement(xml_path: Path) -> bool:
    """True if the XML does not use the <configs> patch root (or is malformed)."""
    try:
        tree = ET.parse(str(xml_path))
        root = tree.getroot()
        return _local_xml_tag(root.tag) != "configs"
    except Exception:
        # Malformed XML is unsafe because it can crash the UI loader.
        return True


def validate_mod_xml_safety(mod_path: Path) -> None:
    """Block deployment of mods that fully replace critical UI XML files.

    7 Days to Die UI XML must use XPath patching (root <configs>). Full-file
    replacements of critical UI files commonly crash the game UI.
    """

    try:
        if not mod_path.exists() or not mod_path.is_dir():
            return
    except Exception:
        return

    mod_name = mod_path.name
    framework = is_framework_mod(mod_name)

    for xml in mod_path.rglob("*.xml"):
        try:
            if not xml.is_file():
                continue
        except Exception:
            continue

        # Requirement: Detect XML files under any Config/ directory.
        try:
            parts_l = [p.lower() for p in xml.parts]
        except Exception:
            parts_l = str(xml).replace("\\", "/").lower().split("/")
        if "config" not in parts_l:
            continue

        if (xml.name or "").strip().lower() in CRITICAL_UI_FILES:
            if is_full_xml_replacement(xml) and (not framework):
                raise RuntimeError(
                    "BLOCKED MOD DEPLOYMENT\n"
                    f"Mod: {mod_name}\n"
                    f"File: {xml}\n"
                    "Reason: Full XML replacement of critical UI file.\n"
                    "Fix: Convert to XPath patching or mark mod as framework."
                )


# ---------------------------------------------------------
# Full-file replacement detection (critical)
# ---------------------------------------------------------


_CRITICAL_RELATIVE_FILES = [
    ("Config/items.xml", {"items"}),
    ("Config/entitygroups.xml", {"entitygroups"}),
    ("Config/sleeper.xml", {"sleeper"}),
    ("Config/quests.xml", {"quests"}),
    ("Config/prefabs.xml", {"prefabs"}),
    ("Config/XUi_Common/styles.xml", {"styles", "configs"}),
    ("Config/XUi_Common/controls.xml", {"controls", "configs"}),
    ("Config/XUi_Menu/controls.xml", {"controls", "configs"}),
    ("Config/XUi_Menu/windows.xml", {"windows", "configs"}),
]


_VANILLA_UI_RELATIVE_FILES = [
    # Warn if these are missing/unparsable in the vanilla game Data/Config tree.
    # (These are frequent UI breakpoints when the game install is corrupt or partially modified.)
    "Data/Config/XUi_Common/styles.xml",
    "Data/Config/XUi_Common/controls.xml",
    "Data/Config/XUi_Menu/controls.xml",
    "Data/Config/XUi_Menu/windows.xml",
]


def _norm_rel(p: Path) -> str:
    try:
        return "/".join([part for part in p.parts])
    except Exception:
        return str(p).replace("\\", "/")


def _matches_critical(relpath: str) -> Optional[Tuple[str, set]]:
    rp = (relpath or "").replace("\\", "/")
    rp_l = rp.lower()
    for crit, roots in _CRITICAL_RELATIVE_FILES:
        if rp_l.endswith(crit.lower()):
            return crit, set(roots)
    return None


def detect_full_file_replacements(*, mod_name: str, mod_path: str) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []
    root = Path(mod_path)
    if not root.exists() or not root.is_dir():
        return issues

    for xml_path in _iter_xml_files(root):
        try:
            rel = _norm_rel(xml_path.relative_to(root))
        except Exception:
            rel = str(xml_path).replace("\\", "/")

        hit = _matches_critical(rel)
        if not hit:
            continue
        crit_name, expected_roots = hit

        # Heuristic: patch-style (xpath) is OK; full-file replacement is risky.
        try:
            if _xml_is_patch_style(xml_path):
                continue
        except Exception:
            # If we can't detect patch ops, be conservative and flag.
            pass

        # If it parses and root looks like a real full file, treat as replacement.
        try:
            tree = ET.parse(str(xml_path))
            rt = (tree.getroot().tag or "").strip().lower()
        except Exception:
            # Invalid XML is handled by integrity checks; still annotate as suspicious.
            rt = ""

        if rt in expected_roots or not rt:
            issues.append(
                ValidationIssue(
                    level="ERROR",
                    reason="full_file_replacement",
                    mod=mod_name,
                    file=crit_name,
                    details=(
                        "Critical file appears to be a FULL replacement (no xpath patch ops detected). "
                        "This commonly breaks UI/gameplay and should be converted to xpath patching."
                    ),
                )
            )

    return issues


# ---------------------------------------------------------
# UI conflict detection + grouping
# ---------------------------------------------------------


_UI_FRAMEWORK_KEYWORDS = [
    "score",
    "xmrcore",
    "quartz",
]


_ORDER_PREFIX_RE = re.compile(r"^(\d+)_")


def _normalize_install_like(name: str) -> str:
    """Normalize folder-like names into a stable comparison key."""
    s = (name or "").strip()
    if s.lower().startswith("__disabled__"):
        s = s[len("__DISABLED__") :]
    m = _ORDER_PREFIX_RE.match(s)
    if m:
        s = s[len(m.group(0)) :]
    return (s or "").strip().lower()


def _parse_modinfo_dependencies(mod_path: Path) -> List[str]:
    """Best-effort parse of dependency-ish fields from ModInfo.xml."""
    modinfo = mod_path / "ModInfo.xml"
    if not modinfo.is_file():
        return []
    try:
        tree = ET.parse(str(modinfo))
        root = tree.getroot()
    except Exception:
        return []

    out: List[str] = []
    for e in root.iter():
        try:
            tag = (e.tag or "").strip().lower()
        except Exception:
            tag = ""
        if tag not in {"requiredmod", "dependencymod", "dependencymods", "dependency", "depend"}:
            continue
        try:
            v = (e.attrib or {}).get("value") or (e.attrib or {}).get("name") or (e.attrib or {}).get("mod")
        except Exception:
            v = None
        if v:
            out.append(str(v).strip())
    return [x for x in out if x]


def validate_dependencies_in_load_order(
    *,
    enabled_mods: Sequence[Tuple[str, str]],
) -> List[ValidationIssue]:
    """Validate that ModInfo.xml declared dependencies exist and load earlier.

    `enabled_mods` order is treated as load order (earlier -> later).
    """
    issues: List[ValidationIssue] = []

    # Build an index of enabled mods by normalized identifier.
    #
    # IMPORTANT: ModInfo.xml dependencies in the wild usually reference the *folder/mod id*,
    # not the UI display name. The GUI passes (display_name, path), so we must index by
    # folder basename derived from path as the primary key, and also index by display name
    # as a fallback for unusual mods that declare dependencies by display name.
    norm_to_display: Dict[str, str] = {}
    norm_to_index: Dict[str, int] = {}
    for idx, (name, path) in enumerate(enabled_mods or []):
        display = str(name or "")
        p = str(path or "")

        try:
            folder = Path(p).name if p else ""
        except Exception:
            folder = ""

        candidate_keys: List[str] = []
        try:
            if folder:
                candidate_keys.append(_normalize_install_like(folder))
        except Exception:
            pass
        try:
            if display:
                candidate_keys.append(_normalize_install_like(display))
        except Exception:
            pass

        for key in candidate_keys:
            if not key:
                continue
            if key not in norm_to_index:
                norm_to_index[key] = idx
                norm_to_display[key] = folder or display

    # Validate each mod's dependencies.
    for idx, (name, path) in enumerate(enabled_mods or []):
        mod_name = str(name or "")
        mod_path = Path(str(path or ""))
        deps = _parse_modinfo_dependencies(mod_path)
        if not deps:
            continue

        for dep_raw in deps:
            dn = _normalize_install_like(dep_raw)
            if not dn:
                continue
            if dn not in norm_to_index:
                issues.append(
                    ValidationIssue(
                        level="ERROR",
                        reason="missing_dependency",
                        mod=mod_name,
                        file="ModInfo.xml",
                        details=f"Dependency is missing/disabled: '{dep_raw}'",
                    )
                )
                continue
            dep_idx = norm_to_index[dn]
            if dep_idx > idx:
                issues.append(
                    ValidationIssue(
                        level="ERROR",
                        reason="dependency_load_order",
                        mod=mod_name,
                        file="ModInfo.xml",
                        details=(f"Dependency loads after dependent: '{dep_raw}' must load before '{mod_name}'."),
                    )
                )

    return issues


def warn_vanilla_ui_files(*, mods_root: str) -> List[ValidationIssue]:
    """Warn if vanilla game UI files appear missing/unparsable.

    We infer the game folder as the parent of the Mods folder.
    """
    issues: List[ValidationIssue] = []
    try:
        game_dir = Path(mods_root).resolve().parent
    except Exception:
        return issues

    for rel in _VANILLA_UI_RELATIVE_FILES:
        p = game_dir / Path(rel)
        if not p.is_file():
            issues.append(
                ValidationIssue(
                    level="WARN",
                    reason="vanilla_ui_missing",
                    file=str(p),
                    details=("Vanilla UI file is missing. Verify game files in Steam/launcher."),
                )
            )
            continue

        try:
            if p.stat().st_size <= 0:
                issues.append(
                    ValidationIssue(
                        level="WARN",
                        reason="vanilla_ui_empty",
                        file=str(p),
                        details="Vanilla UI file is empty (0 bytes). Verify game files.",
                    )
                )
                continue
        except Exception:
            pass

        try:
            ET.parse(str(p))
        except Exception as e:
            issues.append(
                ValidationIssue(
                    level="WARN",
                    reason="vanilla_ui_invalid_xml",
                    file=str(p),
                    details=f"Vanilla UI XML does not parse: {e}",
                )
            )

    return issues


def warn_appdata_cache() -> List[ValidationIssue]:
    """Warn if %AppData%\7DaysToDie contains signals of cached UI/XML state.

    This is best-effort and intentionally conservative: it does not delete anything.
    """
    issues: List[ValidationIssue] = []
    appdata = os.getenv("APPDATA") or ""
    if not appdata:
        return issues
    root = Path(appdata) / "7DaysToDie"
    if not root.exists() or not root.is_dir():
        return issues

    # Look for likely cache artifacts (heuristic).
    try:
        hits = []
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            n = (p.name or "").lower()
            if "xui" in n or "cache" in n or n.endswith(".cache"):
                hits.append(p)
                if len(hits) >= 5:
                    break
        if hits:
            issues.append(
                ValidationIssue(
                    level="WARN",
                    reason="appdata_cached_state",
                    file=str(root),
                    details=(
                        "Cached state exists under %AppData%\\7DaysToDie (possible stale UI/XML cache). "
                        "If you see persistent UI null refs, consider verifying game files and clearing this folder (after backing up saves)."
                    ),
                )
            )
    except Exception:
        pass

    return issues


def _iter_mod_files(mod_path: Path) -> Iterable[Path]:
    try:
        yield from mod_path.rglob("*")
    except Exception:
        return


def mod_touches_xui(mod_path: str) -> bool:
    p = Path(mod_path)
    if not p.exists() or not p.is_dir():
        return False
    for fp in _iter_mod_files(p):
        try:
            if not fp.is_file():
                continue
            # segment match avoids false positives in filenames.
            parts = [str(x) for x in fp.parts]
            if any(part.lower().startswith("xui_") for part in parts):
                return True
            # also treat common pattern Config/XUi_...
            if "xui_" in str(fp).lower():
                # quick accept
                return True
        except Exception:
            continue
    return False


def categorize_ui_mod(*, mod_name: str, mod_path: str) -> str:
    """Return one of: 'framework', 'hud', 'extension', 'unknown'."""
    name_l = (mod_name or "").lower()

    if any(k in name_l for k in _UI_FRAMEWORK_KEYWORDS):
        return "framework"

    # HUD heuristic
    if "hud" in name_l:
        return "hud"

    # File heuristics
    p = Path(mod_path)
    try:
        # UI frameworks often ship shared XUi_Common styles/controls patches.
        for fp in _iter_xml_files(p):
            s = str(fp).replace("\\", "/").lower()
            if "/xui_common/" in s and (s.endswith("styles.xml") or s.endswith("controls.xml")):
                # not always a framework, but treat as framework-adjacent.
                return "framework"
        for fp in _iter_xml_files(p):
            s = str(fp).replace("\\", "/").lower()
            if "/xui_menu/" in s:
                return "hud"
    except Exception:
        pass

    return "extension"


def detect_ui_frameworks(enabled_mods: Sequence[Tuple[str, str]]) -> Dict[str, List[Tuple[str, str]]]:
    """Return mapping framework_keyword -> list(mod_name, mod_path)."""
    out: Dict[str, List[Tuple[str, str]]] = {}
    for name, path in enabled_mods or []:
        n = str(name or "")
        p = str(path or "")
        nl = n.lower()
        for kw in _UI_FRAMEWORK_KEYWORDS:
            if kw in nl:
                out.setdefault(kw, []).append((n, p))
    return out


def ui_group_prefix(category: str) -> str:
    c = (category or "").strip().lower()
    if c == "framework":
        return "0_UIFramework"
    if c == "extension":
        return "1_UIExtensions"
    if c == "hud":
        # HUD mods should load last (last loaded wins for XUi/windows.xml overrides).
        return "2_HUD"
    return ""


# ---------------------------------------------------------
# Preflight (dry-run) runner
# ---------------------------------------------------------


_SAVE_RISK_FILES = {
    "items.xml",
    "entitygroups.xml",
    "sleeper.xml",
    "quests.xml",
    "prefabs.xml",
}


def preflight_check(
    *,
    mods_root: str,
    enabled_mods: Sequence[Tuple[str, str]],
    block_multiple_mods_dirs: bool = True,
    block_invalid_xml: bool = True,
    block_full_file_replacements: bool = True,
    enforce_single_ui_framework: bool = True,
) -> PreflightReport:
    issues: List[ValidationIssue] = []

    # 1) Single Mods directory
    st, dir_issues = validate_single_mods_dir(mods_root=mods_root)
    if block_multiple_mods_dirs:
        issues.extend(dir_issues)
    else:
        for i in dir_issues:
            issues.append(ValidationIssue(level="WARN", reason=i.reason, details=i.details))

    # 2) XML integrity
    for mod_name, mod_path in enabled_mods or []:
        if not block_invalid_xml:
            continue
        issues.extend(validate_mod_xml_tree(mod_name=str(mod_name), mod_path=str(mod_path)))

    # 3) Full-file replacement detection
    if block_full_file_replacements:
        for mod_name, mod_path in enabled_mods or []:
            issues.extend(detect_full_file_replacements(mod_name=str(mod_name), mod_path=str(mod_path)))

    # 4) UI framework conflict
    ui_mods = [(n, p) for (n, p) in (enabled_mods or []) if mod_touches_xui(p)]
    if enforce_single_ui_framework and ui_mods:
        fw = detect_ui_frameworks(ui_mods)
        active_fw = [k for k, v in (fw or {}).items() if v]
        if len(active_fw) > 1:
            details = ["Multiple UI frameworks detected (only one is allowed):"]
            for k in sorted(active_fw):
                names = ", ".join([n for (n, _p) in fw.get(k, [])])
                details.append(f"- {k}: {names}")
            issues.append(
                ValidationIssue(
                    level="ERROR",
                    reason="multiple_ui_frameworks",
                    details="\n".join(details),
                )
            )

    # 5) Dependencies & load order (ModInfo.xml)
    try:
        issues.extend(validate_dependencies_in_load_order(enabled_mods=list(enabled_mods or [])))
    except Exception:
        # Fail-safe: do not crash preflight over dependency parsing
        pass

    # 6) Vanilla file verification awareness + cached state hints
    try:
        issues.extend(warn_vanilla_ui_files(mods_root=str(mods_root)))
    except Exception:
        pass
    try:
        issues.extend(warn_appdata_cache())
    except Exception:
        pass

    # 5) Save safety warnings
    # If any enabled mod touches known save-risk files, warn.
    try:
        for mod_name, mod_path in enabled_mods or []:
            p = Path(mod_path)
            if not p.exists() or not p.is_dir():
                continue
            for xml_path in _iter_xml_files(p):
                if (xml_path.name or "").lower() in _SAVE_RISK_FILES:
                    issues.append(
                        ValidationIssue(
                            level="WARN",
                            reason="save_safety",
                            mod=str(mod_name),
                            file=str(xml_path.name),
                            details=(
                                "This update may corrupt existing saves. Starting a new world is strongly recommended."
                            ),
                        )
                    )
                    break
    except Exception:
        pass

    ok = not any((i.level or "").upper() == "ERROR" for i in issues)
    return PreflightReport(ok=ok, issues=issues, mods_dir_status=st)


def format_report_text(report: PreflightReport) -> str:
    ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    lines: List[str] = []
    lines.append("=== 7DTD Mod Preflight Report ===")
    lines.append(f"Timestamp: {ts}")
    lines.append(f"Result: {'OK' if report.ok else 'BLOCKED'}")
    lines.append("")

    st = report.mods_dir_status
    if st:
        lines.append("Mods directories:")
        lines.append(f"- Game Mods: {st.game_mods_dir} ({'HAS MODS' if st.game_has_mods else 'empty'})")
        lines.append(f"- Documents Mods: {st.documents_mods_dir} ({'HAS MODS' if st.documents_has_mods else 'empty'})")
        lines.append("")

    errs = report.errors
    warns = report.warnings

    if errs:
        lines.append(f"Errors ({len(errs)}):")
        for i in errs:
            where = f" [{i.mod}]" if i.mod else ""
            f = f" ({i.file})" if i.file else ""
            lines.append(f"- {i.reason}{where}{f}: {i.details}")
        lines.append("")

    if warns:
        lines.append(f"Warnings ({len(warns)}):")
        for i in warns:
            where = f" [{i.mod}]" if i.mod else ""
            f = f" ({i.file})" if i.file else ""
            lines.append(f"- {i.reason}{where}{f}: {i.details}")
        lines.append("")

    if not errs and not warns:
        lines.append("No issues detected.")

    return "\n".join(lines).rstrip() + "\n"
