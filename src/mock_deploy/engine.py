import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Tuple
from .state import XMLState
from .mutation import Mutation


def _iter_mutations_from_file(file_path: Path, mod_name: str, order: int) -> List[Mutation]:
    muts: List[Mutation] = []
    try:
        tree = ET.parse(str(file_path))
        root = tree.getroot()
    except Exception:
        return muts

    root_tag = root.tag or "configs"

    # Prefer explicit patch operations when present (7DTD-style)
    has_patch_ops = False
    for elem in root.iter():
        if elem is root:
            continue
        xp = elem.get("xpath")
        if xp:
            has_patch_ops = True
            op = (elem.tag or "").lower()
            if op not in ("set", "append", "remove"):
                # ignore unknown operations
                continue
            text = (elem.text or "").strip()
            # remove operations may not have text
            muts.append(
                Mutation(
                    mod=mod_name,
                    file=str(file_path.name),
                    xpath=xp.strip(),
                    op=op,
                    value=text,
                    order=order,
                )
            )

    if not has_patch_ops:
        # Fallback: treat leaf elements as set operations of their text
        for elem in root.iter():
            if len(list(elem)) == 0:  # leaf
                text = (elem.text or "").strip()
                if not text:
                    continue
                xpath = f"/{root_tag}/{elem.tag}"
                # use name/id when available
                name = elem.get("name") or elem.get("id")
                if name:
                    xpath += f"[@name='{name}']"
                muts.append(
                    Mutation(
                        mod=mod_name,
                        file=str(file_path.name),
                        xpath=xpath,
                        op="set",
                        value=text,
                        order=order,
                    )
                )
    return muts


def simulate_deployment(mods: List[Tuple[str, str]]) -> Tuple[XMLState, list]:
    """
    mods: list of (mod_name, mod_path) in load order
    Returns: (final_state, conflicts)
    """
    state = XMLState()
    seq = 0
    for mod_name, mod_path in mods:
        cfg_dir = Path(mod_path) / "Config"
        if not cfg_dir.is_dir():
            continue
        for xml_file in sorted(cfg_dir.glob("*.xml")):
            muts = _iter_mutations_from_file(xml_file, mod_name, seq)
            for m in muts:
                state.apply(m)
                seq += 1
    return state, state.conflicts
