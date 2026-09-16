from dataclasses import dataclass


@dataclass(slots=True)
class ResultadoAuditoria:
    matricula: int | None
    nome: str
    data: str
    tipo: str
    status: str
    motivo: str
    acao: str
