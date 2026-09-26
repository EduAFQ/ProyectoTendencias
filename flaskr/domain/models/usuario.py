from dataclasses import dataclass


@dataclass(frozen=True)
class Usuario:
    nombre: str
    id: int | None = None