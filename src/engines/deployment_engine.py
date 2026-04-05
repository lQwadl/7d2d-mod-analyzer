from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from deployment.copy_deployer import CopyDeployer
from deployment.file_copy import Logger


@dataclass(frozen=True)
class DeployResult:
    ok: bool
    message: str
    snapshot_id: Optional[str] = None


class DeploymentEngine:
    """Thin facade over a safe, file-driven deployer.

    Invariants:
    - Files drive directory creation.
    - Every copied file is logged immediately before copy.
    - Empty mod folders are treated as fatal deployment errors.
    """

    def __init__(self, *, timeline_path: str = "deployment_timeline.jsonl"):
        # timeline_path retained for API compatibility; timeline events are written by the deployer.
        self.timeline_path = timeline_path
        self._deployer = CopyDeployer()

    def deploy(self, *args, **kwargs) -> DeployResult:
        try:
            self._deployer.deploy(*args, **kwargs)
            return DeployResult(ok=True, message="deployed", snapshot_id=None)
        except Exception as e:
            return DeployResult(ok=False, message=str(e))

    def rollback(self, target_path: str, *, log: Logger | None = None) -> DeployResult:
        try:
            self._deployer.rollback(target_path=target_path)
            if log:
                log("Rollback complete")
            return DeployResult(ok=True, message="rolled back", snapshot_id=None)
        except Exception as e:
            if log:
                log(f"Rollback failed: {e}")
            return DeployResult(ok=False, message=str(e), snapshot_id=None)
