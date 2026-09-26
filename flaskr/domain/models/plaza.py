from dataclasses import dataclass


@dataclass(frozen=True)
class Plaza:
    codigo: str
    id: int | None = None