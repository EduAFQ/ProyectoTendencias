from dataclasses import dataclass


@dataclass(frozen=True)
class Vehiculo:
    matricula: str
    cliente_id: int
    id: int | None = None