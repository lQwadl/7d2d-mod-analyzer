from __future__ import annotations

import shutil
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


def _tmp_root() -> Path:
    # Keep test temp data inside the workspace (never under AppData).
    root = Path(__file__).resolve().parent / "_tmp"
    root.mkdir(parents=True, exist_ok=True)
    return root


@contextmanager
def temp_dir(prefix: str) -> Iterator[Path]:
    path = _tmp_root() / f"{prefix}{uuid.uuid4().hex[:10]}"
    path.mkdir(parents=True, exist_ok=True)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)
