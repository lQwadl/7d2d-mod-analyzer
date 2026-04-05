from dataclasses import dataclass


@dataclass
class Mutation:
    mod: str
    file: str
    xpath: str
    op: str  # 'set' | 'append' | 'remove'
    value: str
    order: int  # application order


@dataclass
class ConflictTrace:
    xpath: str
    file: str
    first: Mutation
    second: Mutation
    kind: str  # 'override' | 'append-append' | 'remove-set' | etc.

    def summary(self) -> str:
        return f"{self.file}:{self.xpath} — {self.first.mod} -> {self.second.mod} ({self.kind})"
