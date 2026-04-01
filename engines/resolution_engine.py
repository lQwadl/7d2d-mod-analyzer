from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, List, Optional, Sequence, Tuple

from models.conflict import Conflict


@dataclass(frozen=True)
class PatchResult:
    patch_dir: Path
    prefer: str
    count: int


@dataclass(frozen=True)
class ResolutionContext:
    """UI-agnostic callbacks for applying resolutions.

    The GUI constructs this with its internal helpers (disable/set-order/scan/etc).
    """

    mods_root: str
    output_root: Optional[str]
    disable_mod: Callable[[str], None]
    set_mod_order: Callable[[str, int], None]
    save_settings: Callable[[], None]
    scan: Callable[[], None]
    apply_load_order: Callable[[], None]


@dataclass(frozen=True)
class OrderAssignment:
    name: str
    order_value: int


def _post_apply(ctx: ResolutionContext) -> None:
    try:
        ctx.save_settings()
    except Exception:
        pass
    try:
        ctx.scan()
    except Exception:
        pass
    try:
        ctx.apply_load_order()
    except Exception:
        pass


def apply_patch_from_sim_payloads(
    ctx: ResolutionContext,
    *,
    sim_conflicts: Sequence[object],
    prefer: str,
) -> PatchResult:
    from logic.conflict_patch import create_conflict_patch

    if prefer not in {"A", "B"}:
        raise RuntimeError(f"Invalid prefer value: {prefer}")

    cts = list(sim_conflicts or [])
    if not cts:
        raise RuntimeError("No conflicts selected")

    patch_dir = create_conflict_patch(
        ctx.mods_root,
        cts,
        prefer=prefer,
        output_root=(ctx.output_root or ctx.mods_root),
    )

    _post_apply(ctx)
    return PatchResult(patch_dir=patch_dir, prefer=prefer, count=len(cts))


def apply_disable_mods(ctx: ResolutionContext, names: Sequence[str]) -> None:
    items = [str(n) for n in (names or []) if str(n or "").strip()]
    if not items:
        raise RuntimeError("No mods selected")
    for n in items:
        ctx.disable_mod(n)
    _post_apply(ctx)


def apply_set_order(ctx: ResolutionContext, assignments: Sequence[OrderAssignment]) -> None:
    items = list(assignments or [])
    if not items:
        raise RuntimeError("No order assignments")
    for a in items:
        ctx.set_mod_order(str(a.name), int(a.order_value))
    _post_apply(ctx)


def apply_reorder_later(
    ctx: ResolutionContext,
    *,
    names: Sequence[str],
    start_order_value: int,
    max_value: int = 99999,
    step: int = 10,
) -> List[OrderAssignment]:
    items = [str(n) for n in (names or []) if str(n or "").strip()]
    if not items:
        raise RuntimeError("No mods selected")

    next_val = int(start_order_value)
    out: List[OrderAssignment] = []
    for n in items:
        ctx.set_mod_order(n, next_val)
        out.append(OrderAssignment(name=n, order_value=next_val))
        next_val = min(int(max_value), next_val + int(step))

    _post_apply(ctx)
    return out


def create_patch_for_conflicts(
    *,
    mods_root: str,
    conflicts: Iterable[Conflict],
    prefer: str,
    output_root: Optional[str] = None,
) -> PatchResult:
    """Create a patch mod for simulator-backed XML override conflicts.

    This is intentionally UI-agnostic (raises RuntimeError on failure).
    """

    from logic.conflict_patch import create_conflict_patch

    selected = list(conflicts or [])
    if not selected:
        raise RuntimeError("No conflicts selected")

    # Only simulator conflicts are patchable today
    cts = []
    for c in selected:
        if c.evidence.source.value != "sim":
            raise RuntimeError("Patching requires simulator-derived conflicts")
        if c.evidence.conflict_type != "xml_override":
            raise RuntimeError(f"Unsupported conflict type for patching: {c.evidence.conflict_type}")
        if not c.payload:
            raise RuntimeError("Missing simulator payload")
        cts.append(c.payload)

    patch_dir = create_conflict_patch(
        mods_root,
        cts,
        prefer=prefer,
        output_root=output_root,
    )

    return PatchResult(patch_dir=patch_dir, prefer=prefer, count=len(cts))
