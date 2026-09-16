from dataclasses import dataclass
from datetime import date


@dataclass(slots=True)
class ExcecaoAutorizada:
    matricula: int
    data_inicio: date
    data_fim: date
    tipo: str
    autorizado: bool | None
    motivo: str
