from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Callable, Iterable, Iterator, Set, Tuple

from .errors import DeploymentError
from ..path_safety import assert_not_appdata


Logger = Callable[[str], None]


def _default_log(message: str) -> None:
    print(message)


def _log(log: Logger | None, message: str) -> None:
    (log or _default_log)(message)


def iter_source_files(source_dir: Path) -> Iterator[Path]:
    # Files drive directory creation. We only consider regular files.
    for p in source_dir.rglob("*"):
        if p.is_file():
            yield p


def ensure_no_overlap(*, source_dir: Path, target_root: Path) -> None:
    """Reject using the target mods folder as a source (or vice-versa)."""
    src = source_dir.resolve()
    tgt = target_root.resolve()

    # AppData is never a valid source or target for mods.
    assert_not_appdata(src, purpose="mod source", exception_cls=DeploymentError)
    assert_not_appdata(tgt, purpose="deploy target", exception_cls=DeploymentError)

    # same path
    if src == tgt:
        raise DeploymentError("Refusing to deploy: source and target are the same directory")

    try:
        src_in_tgt = os.path.commonpath([str(tgt), str(src)]) == str(tgt)
    except Exception:
        src_in_tgt = False

    try:
        tgt_in_src = os.path.commonpath([str(src), str(tgt)]) == str(src)
    except Exception:
        tgt_in_src = False

    if src_in_tgt or tgt_in_src:
        raise DeploymentError(
            "Refusing to deploy: source/target overlap (Steam Mods folder cannot be both source and destination)"
        )


def copy_tree_file_driven(
    *,
    source_dir: Path,
    dest_dir: Path,
    target_root: Path,
    log: Logger | None = None,
) -> Tuple[int, Set[str]]:
    """Copy all files under source_dir into dest_dir, preserving relative paths.

    Returns (files_copied, expected_relative_paths).

    Invariants:
    - No directory is created unless at least one file is copied.
    - Every copied file is logged immediately before the copy.
    """
    if not source_dir.exists() or not source_dir.is_dir():
        raise DeploymentError(f"Source mod folder missing: {source_dir}")

    ensure_no_overlap(source_dir=source_dir, target_root=target_root)

    # Destination mod folder must also not be under AppData.
    assert_not_appdata(dest_dir, purpose="deploy destination", exception_cls=DeploymentError)

    copied = 0
    expected: Set[str] = set()

    for src_file in iter_source_files(source_dir):
        rel = os.path.relpath(str(src_file), str(source_dir))
        expected.add(rel)
        dst_file = dest_dir / rel

        # Create only the parent directory needed for this file.
        dst_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            size = os.path.getsize(src_file)
        except OSError:
            size = -1

        _log(log, f"COPY FILE: {src_file} -> {dst_file} ({size} bytes)")

        try:
            shutil.copy2(str(src_file), str(dst_file))
        except Exception as e:
            raise DeploymentError(f"Copy failed: {src_file} -> {dst_file}: {e}")

        # Validate copy (size match). This catches post-copy truncation / partial writes.
        try:
            src_size = os.path.getsize(src_file)
            dst_size = os.path.getsize(dst_file)
        except OSError as e:
            raise DeploymentError(f"Copy validation failed: {src_file} -> {dst_file}: {e}")

        if src_size != dst_size:
            raise DeploymentError(
                f"Copy validation failed (size mismatch): {src_file} ({src_size}) -> {dst_file} ({dst_size})"
            )

        copied += 1

    if copied == 0:
        raise DeploymentError(f"Deployment produced no files (empty source?): {source_dir}")

    # Post-deploy validation: destination must contain at least one file.
    if not any(p.is_file() for p in dest_dir.rglob("*")):
        raise DeploymentError(f"Deployment produced empty mod folder: {dest_dir}")

    return copied, expected


def delete_extra_files(
    *,
    dest_dir: Path,
    keep_relpaths: Set[str],
    log: Logger | None = None,
) -> None:
    """Delete files in dest_dir that are not present in keep_relpaths.

    This runs only after a successful copy, so deletion never happens before replacement is confirmed.
    """
    if not dest_dir.exists() or not dest_dir.is_dir():
        return

    # Delete stray files.
    for p in list(dest_dir.rglob("*")):
        if not p.is_file():
            continue
        rel = os.path.relpath(str(p), str(dest_dir))
        if rel not in keep_relpaths:
            try:
                _log(log, f"DELETE FILE (post-copy cleanup): {p}")
                p.unlink()
            except Exception as e:
                raise DeploymentError(f"Cleanup failed deleting {p}: {e}")

    # Remove empty directories bottom-up.
    for p in sorted([d for d in dest_dir.rglob("*") if d.is_dir()], key=lambda x: len(x.parts), reverse=True):
        try:
            if not any(p.iterdir()):
                p.rmdir()
        except Exception as e:
            raise DeploymentError(f"Cleanup failed removing empty dir {p}: {e}")
