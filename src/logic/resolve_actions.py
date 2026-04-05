import os
import pathlib

from logic.rename_sanitizer import apply_prefix_width, sanitize_name

DISABLED_PREFIX = "__DISABLED__"


def disable_mod_folder(mod_path: str) -> str:
    """Disable a mod by renaming its folder to start with `__DISABLED__`.

    Returns the new path.

    Raises RuntimeError on failure.
    """
    old_path = pathlib.Path(mod_path)
    if not old_path.exists():
        raise RuntimeError(f"Mod folder does not exist: {old_path}")

    if old_path.name.startswith(DISABLED_PREFIX):
        return str(old_path)

    new_path = old_path.parent / f"{DISABLED_PREFIX}{old_path.name}"
    if new_path.exists():
        raise RuntimeError(f"Disable target already exists: {new_path}")

    try:
        os.rename(str(old_path), str(new_path))
    except Exception as e:
        raise RuntimeError(f"Failed to disable mod folder: {e}")

    return str(new_path)


def set_mod_order_prefix(mod_path: str, order_value: int) -> str:
    """Rename a mod folder to have a numeric `NNN_` prefix.

    Preserves `__DISABLED__` prefix if present.

    Returns the new path.

    Raises RuntimeError on failure.
    """
    if order_value < 0 or order_value > 99999:
        raise RuntimeError("Order must be between 0 and 99999")

    old_path = pathlib.Path(mod_path)
    if not old_path.exists():
        raise RuntimeError(f"Mod folder does not exist: {old_path}")

    folder = old_path.name
    disabled = False
    if folder.startswith(DISABLED_PREFIX):
        disabled = True
        folder = folder[len(DISABLED_PREFIX) :]

    clean = sanitize_name(folder)
    width = max(3, len(str(int(order_value))))
    new_base = apply_prefix_width(int(order_value), clean, width=width)
    new_name = (DISABLED_PREFIX if disabled else "") + new_base
    new_path = old_path.parent / new_name

    if new_path.exists():
        raise RuntimeError(f"Order target already exists: {new_path}")

    try:
        os.rename(str(old_path), str(new_path))
    except Exception as e:
        raise RuntimeError(f"Failed to set mod order prefix: {e}")

    return str(new_path)
