from dataclasses import dataclass


@dataclass(frozen=True)
class Cliente:
    nombre: str
    email: str | None = None
    id: int | None = None