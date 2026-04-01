import re

PREFIX_RE = re.compile(r"^(\d+_)+(.+)$")


def sanitize_name(name: str) -> str:
    match = PREFIX_RE.match(name)
    return match.group(2) if match else name


def apply_prefix(order: int, name: str) -> str:
    return apply_prefix_width(order, name, width=3)


def apply_prefix_width(order: int, name: str, *, width: int) -> str:
    clean = sanitize_name(name)
    try:
        w = int(width)
    except Exception:
        w = 3
    if w < 1:
        w = 1
    return f"{int(order):0{w}d}_{clean}"
