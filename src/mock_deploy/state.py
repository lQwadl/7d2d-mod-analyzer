from typing import Dict, List, Tuple
from .mutation import Mutation, ConflictTrace


class XMLState:
    def __init__(self) -> None:
        # current values per xpath
        self.values: Dict[Tuple[str, str], str] = {}
        # last mutation applied per (file, xpath)
        self.last_mut: Dict[Tuple[str, str], Mutation] = {}
        self.conflicts: List[ConflictTrace] = []

    def apply(self, m: Mutation) -> None:
        key = (m.file, m.xpath)
        prev = self.last_mut.get(key)
        if prev:
            kind = self._classify(prev, m)
            # record conflict when two different mods touch same target
            if prev.mod != m.mod:
                self.conflicts.append(
                    ConflictTrace(
                        xpath=m.xpath, file=m.file, first=prev, second=m, kind=kind
                    )
                )
        # apply mutation semantics (simplified)
        if m.op in ("set", "append"):
            self.values[key] = (
                m.value if m.op == "set" else (self.values.get(key, "") + m.value)
            )
        elif m.op == "remove":
            self.values.pop(key, None)
        self.last_mut[key] = m

    @staticmethod
    def _classify(a: Mutation, b: Mutation) -> str:
        if a.op == "set" and b.op == "set":
            return "override"
        if a.op == "append" and b.op == "append":
            return "append-append"
        return f"{a.op}-{b.op}"
