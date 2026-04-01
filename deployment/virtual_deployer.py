from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

from deployment.copy_deployer import CopyDeployer
from deployment.errors import DeploymentError
from deployment.file_copy import Logger


@dataclass(frozen=True)
class DeploymentSnapshot:
    id: str
    created_at: float
    target_path: str
    backup_path: str
    method: str


def _now_ts() -> str:
    return time.strftime("%Y%m%d_%H%M%S", time.localtime())


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _write_json(path: Path, data: dict) -> None:
    _ensure_dir(path.parent)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


class VirtualDeployer:
    """Safe, file-driven deployer.

    Legacy behavior (junction/symlink/hardlink + atomic swap) has been removed.
    Those approaches can leave the target Mods directory in an unsafe or empty state
    if anything fails mid-operation or if cleanup triggers unexpectedly.
    """

    def __init__(self, *, store_path: str = os.path.join("data", "deployments.json")):
        self.store_path = Path(store_path)
        self._store = self._load_store()
        self._copy = CopyDeployer()

    def _load_store(self) -> dict:
        if not self.store_path.exists():
            return {"version": 1, "snapshots": []}
        d = _read_json(self.store_path)
        if not isinstance(d, dict):
            return {"version": 1, "snapshots": []}
        d.setdefault("version", 1)
        d.setdefault("snapshots", [])
        return d

    def _save_store(self) -> None:
        _write_json(self.store_path, self._store)

    def list_snapshots(self, *, target_path: str) -> List[DeploymentSnapshot]:
        out: List[DeploymentSnapshot] = []
        for s in self._store.get("snapshots") or []:
            try:
                if str(s.get("target_path")) != str(target_path):
                    continue
                out.append(
                    DeploymentSnapshot(
                        id=str(s.get("id")),
                        created_at=float(s.get("created_at")),
                        target_path=str(s.get("target_path")),
                        backup_path=str(s.get("backup_path")),
                        method=str(s.get("method")),
                    )
                )
            except Exception:
                continue
        out.sort(key=lambda ss: ss.created_at, reverse=True)
        return out

    def deploy(
        self,
        *,
        source_mod_dirs: List[Tuple[str, str]],
        target_path: str,
        method: str = "copy",
        timeline_path: str = os.path.join("data", "deployment_timeline.jsonl"),
        log: Logger | None = None,
    ) -> DeploymentSnapshot:
        """Deploy a list of (dest_folder_name, source_path) into target_path.

        This deployer is intentionally file-driven:
        - Files drive directory creation.
        - Every file copy is logged immediately before copy.
        - Empty mod folders are treated as fatal deployment errors.
        """

        if method != "copy":
            raise DeploymentError(
                f"Unsupported deploy method '{method}'. Only 'copy' is allowed to prevent empty/unsafe Mods states."
            )

        ts = _now_ts()
        tgt = Path(target_path)

        # Perform a safe copy deployment.
        self._copy.deploy(source_mod_dirs=source_mod_dirs, target_path=target_path, log=log, clean_destination=True)

        snap = DeploymentSnapshot(
            id=str(ts),
            created_at=time.time(),
            target_path=str(tgt),
            backup_path="",
            method="copy",
        )

        self._store.setdefault("snapshots", [])
        self._store["snapshots"].append(
            {
                "id": snap.id,
                "created_at": snap.created_at,
                "target_path": snap.target_path,
                "backup_path": snap.backup_path,
                "method": snap.method,
            }
        )
        self._save_store()

        # timeline event (best effort, but never silent)
        try:
            _ensure_dir(Path(timeline_path).parent)
            with open(timeline_path, "a", encoding="utf-8") as f:
                f.write(
                    json.dumps(
                        {
                            "ts": time.time(),
                            "event": "deploy",
                            "target": snap.target_path,
                            "method": snap.method,
                            "snapshot_id": snap.id,
                            "count": len(source_mod_dirs or []),
                        }
                    )
                    + "\n"
                )
        except Exception as e:
            if log:
                log(f"WARN: failed writing deployment timeline: {e}")

        return snap

    def rollback(
        self,
        *,
        target_path: str,
        timeline_path: str = os.path.join("data", "deployment_timeline.jsonl"),
        log: Logger | None = None,
    ) -> None:
        # Copy deploy rollback: remove last deployed folders according to manifest.
        self._copy.rollback(target_path=target_path)

        try:
            _ensure_dir(Path(timeline_path).parent)
            with open(timeline_path, "a", encoding="utf-8") as f:
                f.write(
                    json.dumps(
                        {
                            "ts": time.time(),
                            "event": "rollback",
                            "target": str(Path(target_path)),
                        }
                    )
                    + "\n"
                )
        except Exception as e:
            if log:
                log(f"WARN: failed writing rollback timeline: {e}")
