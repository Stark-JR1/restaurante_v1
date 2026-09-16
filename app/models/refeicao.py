from dataclasses import dataclass
from datetime import date


@dataclass(slots=True)
class Refeicao:
    matricula: int
    data: date
    tipo: str
