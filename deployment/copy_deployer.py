from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

from deployment.errors import DeploymentError
from deployment.file_copy import Logger, copy_tree_file_driven, delete_extra_files
from logic.deployment_guardrails import validate_mod_xml_safety
from path_safety import assert_not_appdata


@dataclass(frozen=True)
class CopyDeployResult:
    deployed_count: int
    target_path: str
    created_at: float
    manifest_path: str


def _now_ts() -> str:
    return time.strftime("%Y%m%d_%H%M%S", time.localtime())


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _safe_read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _safe_write_json(path: Path, data: dict) -> None:
    _ensure_dir(path.parent)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _target_key(target_path: str) -> str:
    s = os.path.abspath(target_path)
    h = hashlib.sha1(s.encode("utf-8", errors="ignore")).hexdigest()
    return h


class CopyDeployer:
    """Copy-only deployer.

    Guardrails:
    - Only creates/removes subfolders inside target Mods folder.
    - Never renames the target folder or its parent.
    - No snapshots inside Steam paths (no atomic swap).

    This is intentionally conservative to avoid WinError 5 on Steam installs.
    """

    def __init__(self, *, manifests_dir: str = os.path.join("data", "deploy_manifests")):
        self.manifests_dir = Path(manifests_dir)

    def _manifest_path(self, target_path: str) -> Path:
        key = _target_key(target_path)
        return self.manifests_dir / f"{key}.json"

    def _load_previous(self, target_path: str) -> List[str]:
        mp = self._manifest_path(target_path)
        d = _safe_read_json(mp)
        names = d.get("deployed_folders") or []
        if not isinstance(names, list):
            return []
        out = []
        for n in names:
            s = str(n or "").strip()
            if s:
                out.append(s)
        return out

    def _save_manifest(self, *, target_path: str, deployed_folders: List[str]) -> Path:
        mp = self._manifest_path(target_path)
        _safe_write_json(
            mp,
            {
                "version": 1,
                "target_path": os.path.abspath(target_path),
                "ts": _now_ts(),
                "deployed_folders": list(deployed_folders or []),
            },
        )
        return mp

    def _assert_within_target(self, target: Path, child: Path) -> None:
        t = target.resolve()
        c = child.resolve()
        try:
            if os.path.commonpath([str(t), str(c)]) != str(t):
                raise RuntimeError("Refusing to operate outside deploy target")
        except Exception:
            raise RuntimeError("Refusing to operate outside deploy target")

    def deploy(
        self,
        *,
        source_mod_dirs: List[Tuple[str, str]],
        target_path: str,
        log: Logger | None = None,
        clean_destination: bool = True,
    ) -> CopyDeployResult:
        tgt = Path(target_path)
        assert_not_appdata(tgt, purpose="deploy target", exception_cls=DeploymentError)
        parent = tgt.parent
        if not parent.exists():
            raise RuntimeError(f"Deploy target parent does not exist: {parent}")
        if not tgt.exists():
            # Allowed: create the Mods folder itself.
            tgt.mkdir(parents=False, exist_ok=True)
        if not tgt.is_dir():
            raise RuntimeError(f"Deploy target is not a directory: {tgt}")

        # Normalize and validate destination names early.
        desired: List[str] = []
        for dest_name, _src_path in source_mod_dirs or []:
            dn = str(dest_name or "").strip()
            if not dn:
                raise DeploymentError("Invalid destination folder name")
            if os.sep in dn or (os.altsep and os.altsep in dn):
                raise DeploymentError(f"Invalid destination folder name (must be a simple folder name): {dn}")
            if dn in (".", ".."):
                raise DeploymentError(f"Invalid destination folder name: {dn}")
            desired.append(dn)

        # Copy current deployment (file-driven). IMPORTANT: no deletions occur before a successful copy.
        deployed: List[str] = []
        existed_before: dict[str, bool] = {}
        for (dest_name, src_path), dn in zip((source_mod_dirs or []), desired):
            src = Path(src_path)

            # HARD STOP if mod contains unsafe UI XML full replacements.
            # Must run before any files are copied.
            validate_mod_xml_safety(src)

            dest = tgt / dn
            self._assert_within_target(tgt, dest)

            existed_before[dn] = dest.exists()

            copied, expected = copy_tree_file_driven(
                source_dir=src,
                dest_dir=dest,
                target_root=tgt,
                log=log,
            )
            if copied <= 0:
                raise DeploymentError(f"Deployment produced no files for mod: {dn}")

            if clean_destination:
                delete_extra_files(dest_dir=dest, keep_relpaths=expected, log=log)

            # Per-mod post validation: a deployed mod folder may never be empty.
            if not any(p.is_file() for p in dest.rglob("*")):
                raise DeploymentError(f"Deployment produced empty mod folder: {dest}")

            deployed.append(dn)

        # Cleanup previous deployment folders (only those we previously deployed AND are not desired now).
        # This runs AFTER a successful deployment to avoid deleting working mods when a deploy fails.
        prev = self._load_previous(str(tgt))
        prev_set = set(prev)
        desired_set = set(deployed)
        for name in sorted(prev_set - desired_set):
            p = tgt / name
            try:
                self._assert_within_target(tgt, p)
                if p.exists() and p.is_dir():
                    shutil.rmtree(str(p), ignore_errors=False)
            except FileNotFoundError:
                continue
            except Exception as e:
                raise DeploymentError(f"Failed cleaning previous deployment folder {p}: {e}")

        # Global validation: if any deployed folder is empty, treat as fatal.
        for dn in deployed:
            p = tgt / dn
            if p.exists() and p.is_dir() and not any(pp.is_file() for pp in p.rglob("*")):
                # Roll back newly created empty folder(s) so no empty state persists.
                if not existed_before.get(dn, False):
                    try:
                        shutil.rmtree(str(p), ignore_errors=False)
                    except Exception as e:
                        raise DeploymentError(
                            f"Fatal deployment error: mod folder exists but contains no files AND rollback cleanup failed ({p}): {e}"
                        )
                raise DeploymentError(f"Fatal deployment error: mod folder exists but contains no files: {p}")

        mp = self._save_manifest(target_path=str(tgt), deployed_folders=deployed)
        return CopyDeployResult(
            deployed_count=len(deployed),
            target_path=str(tgt),
            created_at=time.time(),
            manifest_path=str(mp),
        )

    def rollback(self, *, target_path: str) -> None:
        """Rollback for copy deploy: remove the last deployed folders only."""
        tgt = Path(target_path)
        if not tgt.exists() or not tgt.is_dir():
            raise RuntimeError("Deploy target does not exist")

        prev = self._load_previous(str(tgt))
        for name in prev:
            p = tgt / name
            self._assert_within_target(tgt, p)
            if p.exists() and p.is_dir():
                shutil.rmtree(str(p), ignore_errors=False)

        # Clear manifest
        self._save_manifest(target_path=str(tgt), deployed_folders=[])
