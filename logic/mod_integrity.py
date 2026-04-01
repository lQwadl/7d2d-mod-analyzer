import hashlib
from pathlib import Path


def hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def hash_mod_folder(mod_path: Path) -> dict:
    hashes = {}
    for file in mod_path.rglob("*"):
        if file.is_file():
            hashes[str(file.relative_to(mod_path))] = hash_file(file)
    return hashes
