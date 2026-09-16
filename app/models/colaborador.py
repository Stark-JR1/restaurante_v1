from dataclasses import dataclass


@dataclass(slots=True)
class Colaborador:
    matricula: int
    nome: str
