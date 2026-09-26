from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Parking:
    vehiculo_id: int
    plaza_id: int
    usuario_id: int
    entrada: datetime
    salida: datetime | None = None
    id: int | None = None